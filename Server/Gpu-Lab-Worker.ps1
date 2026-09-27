# Private control channel over local pipes or pinned SSH; never an HTTP service.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
[Console]::OutputEncoding = [Text.UTF8Encoding]::new($false)
Add-Type -TypeDefinition @'
using System;
using System.Diagnostics;
using System.Runtime.InteropServices;
using System.Collections.Concurrent;
using System.Threading;
public sealed class GpuLabJob : IDisposable {
    [StructLayout(LayoutKind.Sequential)] struct Basic {
        public long perProcess, perJob; public uint flags; public UIntPtr min, max;
        public uint active; public UIntPtr affinity; public uint priority, scheduling;
    }
    [StructLayout(LayoutKind.Sequential)] struct Io { public ulong a,b,c,d,e,f; }
    [StructLayout(LayoutKind.Sequential)] struct Extended {
        public Basic basic; public Io io; public UIntPtr processMemory, jobMemory, peakProcess, peakJob;
    }
    [DllImport("kernel32.dll", CharSet=CharSet.Unicode)] static extern IntPtr CreateJobObject(IntPtr a, string n);
    [DllImport("kernel32.dll")] static extern bool SetInformationJobObject(IntPtr j, int c, IntPtr p, uint s);
    [DllImport("kernel32.dll")] static extern bool AssignProcessToJobObject(IntPtr j, IntPtr p);
    [DllImport("kernel32.dll")] static extern bool IsProcessInJob(IntPtr p, IntPtr j, out bool result);
    [DllImport("kernel32.dll")] static extern bool CloseHandle(IntPtr h);
    [DllImport("iphlpapi.dll")] static extern uint GetExtendedTcpTable(IntPtr table, ref int size, bool order, int family, int kind, uint reserved);
    public static bool OwnsListener(int pid, int port) {
        int size=0; GetExtendedTcpTable(IntPtr.Zero,ref size,false,2,3,0);
        if(size<4 || size>16777216) throw new Exception("TCP_TABLE_UNAVAILABLE");
        IntPtr table=Marshal.AllocHGlobal(size);
        try {
            if(GetExtendedTcpTable(table,ref size,false,2,3,0)!=0) throw new Exception("TCP_TABLE_UNAVAILABLE");
            int count=Marshal.ReadInt32(table); if(count<0 || count>(size-4)/24) throw new Exception("TCP_TABLE_INVALID");
            int found=0;
            for(int i=0;i<count;i++) {
                int offset=4+i*24, raw=Marshal.ReadInt32(table,offset+8);
                int actual=((raw & 255)<<8) | ((raw>>8)&255);
                if(actual!=port) continue;
                if(Marshal.ReadInt32(table,offset+4)!=0x0100007f || Marshal.ReadInt32(table,offset+20)!=pid) return false;
                found++;
            }
            return found==1;
        } finally { Marshal.FreeHGlobal(table); }
    }
    IntPtr job;
    public Process Child;
    public GpuLabJob() {
        job=CreateJobObject(IntPtr.Zero,null);
        var e=new Extended(); e.basic.flags=0x2000; // KILL_ON_JOB_CLOSE
        int size=Marshal.SizeOf(e); IntPtr ptr=Marshal.AllocHGlobal(size);
        try { Marshal.StructureToPtr(e,ptr,false);
            if(job==IntPtr.Zero || !SetInformationJobObject(job,9,ptr,(uint)size)) throw new Exception("JOB_CREATE_FAILED");
        } catch { Dispose(); throw; } finally { Marshal.FreeHGlobal(ptr); }
    }
    public void Start(ProcessStartInfo info) {
        info.UseShellExecute=false; info.CreateNoWindow=true;
        info.RedirectStandardOutput=true; info.RedirectStandardError=true;
        Child=new Process(); Child.StartInfo=info;
        // Drain logs without retaining prompts, paths or unbounded output.
        Child.OutputDataReceived += (s,e)=>{}; Child.ErrorDataReceived += (s,e)=>{};
        if(!Child.Start()) throw new Exception("OLLAMA_START_FAILED");
        if(!AssignProcessToJobObject(job,Child.Handle)) {
            try { Child.Kill(); } catch {} throw new Exception("JOB_ASSIGN_FAILED");
        }
        Child.BeginOutputReadLine(); Child.BeginErrorReadLine();
    }
    public bool Contains(int pid) {
        try { using(var p=Process.GetProcessById(pid)) { bool found; return IsProcessInJob(p.Handle,job,out found) && found; } }
        catch { return false; }
    }
    public void Dispose() {
        if(job!=IntPtr.Zero) { CloseHandle(job); job=IntPtr.Zero; }
        if(Child!=null) { try { Child.WaitForExit(5000); } catch {} Child.Dispose(); Child=null; }
    }
}
public sealed class GpuLabInput {
    BlockingCollection<string> lines=new BlockingCollection<string>(16);
    public GpuLabInput() {
        var thread=new Thread(()=>{ try { string s; while((s=Console.ReadLine())!=null) {
            if(s.Length>131072) break; lines.Add(s);
        }} finally { lines.CompleteAdding(); }}); thread.IsBackground=true; thread.Start();
    }
    public string Next() { string s; return lines.TryTake(out s,60000) ? s : null; }
}
'@

function Send-GpuReply($value) { [Console]::WriteLine(($value | ConvertTo-Json -Depth 12 -Compress)) }
function Invoke-GpuProbe([string]$arguments) {
    $si = [Diagnostics.ProcessStartInfo]::new()
    $si.FileName = $script:smi; $si.Arguments = $arguments
    $si.UseShellExecute = $false; $si.CreateNoWindow = $true
    $si.RedirectStandardOutput = $true; $si.RedirectStandardError = $true
    $proc = [Diagnostics.Process]::new(); $proc.StartInfo = $si
    try {
        if (-not $proc.Start()) { throw 'NVIDIA_SMI_START_FAILED' }
        $out = $proc.StandardOutput.ReadToEndAsync(); $err = $proc.StandardError.ReadToEndAsync()
        if (-not $proc.WaitForExit(8000)) { $proc.Kill(); throw 'NVIDIA_SMI_TIMEOUT' }
        if ($proc.ExitCode -ne 0) { throw 'NVIDIA_SMI_QUERY_FAILED' }
        if ($out.Result.Length -gt 131072) { throw 'NVIDIA_SMI_OUTPUT_LIMIT' }
        return $out.Result
    } finally { $proc.Dispose() }
}
function Get-GpuInventory {
    $raw = Invoke-GpuProbe '--query-gpu=uuid,name,memory.total,driver_version --format=csv,noheader,nounits'
    $rows = @($raw -split '\r?\n' | Where-Object { $_.Trim() } | ConvertFrom-Csv -Header uuid,name,memory_mib,driver)
    foreach ($r in $rows) { foreach ($p in $r.PSObject.Properties) { $p.Value = $p.Value.Trim() } }
    return $rows
}
function Get-GpuSample {
    $raw = Invoke-GpuProbe '--query-gpu=uuid,memory.used,utilization.gpu,temperature.gpu,power.draw --format=csv,noheader,nounits'
    $gpus = @($raw -split '\r?\n' | Where-Object { $_.Trim() } | ConvertFrom-Csv -Header uuid,memory_mib,utilization,temperature_c,power_w)
    foreach ($r in $gpus) { foreach ($p in $r.PSObject.Properties) { $p.Value = $p.Value.Trim() } }
    $apps = @(); $owned = @(); $available = $true
    try {
        $raw = Invoke-GpuProbe '--query-compute-apps=gpu_uuid,pid,used_gpu_memory --format=csv,noheader,nounits'
        foreach ($r in @($raw -split '\r?\n' | Where-Object { $_.Trim() } | ConvertFrom-Csv -Header uuid,pid,memory_mib)) {
            $row = @{uuid=$r.uuid.Trim();pid=[int]$r.pid.Trim();memory_mib=$r.memory_mib.Trim()}
            $apps += $row
            if ($script:labJob -and $script:labJob.Contains($row.pid)) { $owned += $row.pid }
        }
    } catch { $available = $false }
    return @{gpus=$gpus;processes=$apps;owned_pids=@($owned | Select-Object -Unique);process_query_available=$available}
}
function Assert-GpuListener {
    if (-not $script:labJob -or $script:labJob.Child.HasExited) { throw 'LAB_PROCESS_EXITED' }
    if (-not [GpuLabJob]::OwnsListener($script:labJob.Child.Id, $script:labPort)) { throw 'LAB_LISTENER_NOT_OWNED' }
}
$script:labJob = $null; $script:labPort = 0; $mutex = $null; $locked = $false
try {
    $smiCommand = Get-Command nvidia-smi.exe -ErrorAction SilentlyContinue
    if (-not $smiCommand) { Send-GpuReply @{ok=$false;error='NVIDIA_SMI_NOT_FOUND'}; return }
    $script:smi = $smiCommand.Source
    $channel = [GpuLabInput]::new()
    Send-GpuReply @{ok=$true;protocol=1;platform='windows'}
    while ($null -ne ($line = $channel.Next())) {
        try {
            $req = $line | ConvertFrom-Json
            $data = @{}
            switch ($req.action) {
                'inventory' { $data = @{gpus=@(Get-GpuInventory)} }
                'sample' { $data = Get-GpuSample }
                'guard' { Assert-GpuListener; $data = @{owned=$true} }
                'start' {
                    if ($script:labJob) { throw 'LAB_ALREADY_RUNNING' }
                    if (-not $locked) {
                        $mutex = [Threading.Mutex]::new($false,'Global\BULL_GPU_Lab_v1')
                        try { $locked = $mutex.WaitOne(0) } catch [Threading.AbandonedMutexException] { $locked = $true }
                        if (-not $locked) { throw 'ANOTHER_GPU_LAB_IS_RUNNING' }
                    }
                    $inventory = @(Get-GpuInventory)
                    $selected = @($req.devices)
                    if ($selected.Count -lt 1 -or $selected.Count -gt 8 -or @($selected | Select-Object -Unique).Count -ne $selected.Count) { throw 'INVALID_GPU_SELECTION' }
                    foreach ($u in $selected) { if ($u -notmatch '^GPU-[0-9a-fA-F]{8}(-[0-9a-fA-F]{4}){3}-[0-9a-fA-F]{12}$' -or $u -notin $inventory.uuid) { throw 'GPU_NOT_PRESENT' } }
                    $exe = [string]$req.executable
                    if (-not $exe) {
                        $cmd = Get-Command ollama.exe -ErrorAction SilentlyContinue
                        if ($cmd) { $exe = $cmd.Source }
                        else { $exe = Join-Path $env:LOCALAPPDATA 'Programs\Ollama\ollama.exe' }
                    }
                    if (-not [IO.Path]::IsPathRooted($exe) -or -not (Test-Path -LiteralPath $exe -PathType Leaf) -or [IO.Path]::GetExtension($exe) -ine '.exe') { throw 'OLLAMA_EXE_NOT_FOUND' }
                    $listener = [Net.Sockets.TcpListener]::new([Net.IPAddress]::Loopback,0)
                    $listener.Start(); $script:labPort = $listener.LocalEndpoint.Port; $listener.Stop()
                    $info = [Diagnostics.ProcessStartInfo]::new(); $info.FileName = $exe; $info.Arguments = 'serve'
                    # Remove inherited tuning/proxy overrides; child environment only.
                    foreach ($key in @($info.EnvironmentVariables.Keys)) {
                        if ($key -match '^(OLLAMA_|CUDA_VISIBLE|GGML_|LLAMA_|ROCR_|HIP_VISIBLE|HSA_OVERRIDE|GPU_DEVICE|HTTP_PROXY$|HTTPS_PROXY$|ALL_PROXY$)') { $info.EnvironmentVariables.Remove($key) }
                    }
                    $settings = @{ CUDA_VISIBLE_DEVICES=($selected -join ','); OLLAMA_HOST="127.0.0.1:$script:labPort";
                        OLLAMA_SCHED_SPREAD=$(if ($selected.Count -gt 1) {'1'} else {'0'}); OLLAMA_NO_CLOUD='1';
                        OLLAMA_VULKAN='0'; GGML_VK_VISIBLE_DEVICES='-1'; ROCR_VISIBLE_DEVICES='-1'; HIP_VISIBLE_DEVICES='-1';
                        OLLAMA_FLASH_ATTENTION='0'; OLLAMA_KV_CACHE_TYPE='f16'; OLLAMA_NUM_PARALLEL='1';
                        OLLAMA_MAX_LOADED_MODELS='1'; OLLAMA_KEEP_ALIVE='5m'; OLLAMA_NOPRUNE='1';
                        OLLAMA_DEBUG_LOG_REQUESTS='0'; OLLAMA_DEBUG='0'; OLLAMA_LOAD_TIMEOUT='10m' }
                    foreach ($key in $settings.Keys) { $info.EnvironmentVariables[$key] = $settings[$key] }
                    $models = [string]$req.models_dir
                    if (-not $models) { $models = $env:OLLAMA_MODELS }
                    if ($models) {
                        if (-not [IO.Path]::IsPathRooted($models) -or -not (Test-Path -LiteralPath $models -PathType Container)) { throw 'MODELS_DIRECTORY_NOT_FOUND' }
                        $info.EnvironmentVariables['OLLAMA_MODELS'] = $models
                    }
                    $script:labJob = [GpuLabJob]::new()
                    try {
                        $script:labJob.Start($info)
                        $ready = $false; $lastGuard = 'OLLAMA_LISTENER_TIMEOUT'
                        for ($i=0; $i -lt 40; $i++) {
                            if ($script:labJob.Child.HasExited) { throw 'OLLAMA_START_FAILED' }
                            try { Assert-GpuListener; $ready = $true; break } catch { $lastGuard = $_.Exception.Message; Start-Sleep -Milliseconds 250 }
                        }
                        if (-not $ready) { throw $lastGuard }
                        $data = @{port=$script:labPort;pid=$script:labJob.Child.Id;environment=$settings;models_dir_explicit=[bool]$models}
                    } catch { $script:labJob.Dispose(); $script:labJob = $null; throw }
                }
                'stop' {
                    if ($script:labJob) { $script:labJob.Dispose(); $script:labJob = $null }
                    $data = @{stopped=$true}
                }
                'exit' { break }
                default { throw 'UNKNOWN_LAB_ACTION' }
            }
            Send-GpuReply @{ok=$true;data=$data}
            if ($req.action -eq 'exit') { break }
        } catch {
            # Only stable codes leave the supervisor, not exception paths/endpoints.
            $msg = [string]$_.Exception.Message
            if ($msg -notmatch '^[A-Z][A-Z0-9_]{2,80}$') { $msg = 'WORKER_OPERATION_FAILED' }
            Send-GpuReply @{ok=$false;error=$msg}
        }
    }
} finally {
    if ($script:labJob) { $script:labJob.Dispose() }
    if ($locked) { $mutex.ReleaseMutex() }
    if ($mutex) { $mutex.Dispose() }
}
