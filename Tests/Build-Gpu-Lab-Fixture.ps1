param([Parameter(Mandatory=$true)][string]$Destination)
# Offline test executables only, built inside caller-owned TemporaryDirectory.
$ErrorActionPreference = 'Stop'
if (-not (Test-Path -LiteralPath $Destination -PathType Container)) { throw 'Missing test directory' }
Add-Type -OutputAssembly (Join-Path $Destination 'nvidia-smi.exe') -OutputType ConsoleApplication -TypeDefinition @'
using System;
using System.Diagnostics;
public static class FakeSmi {
    public static void Main(string[] args) {
        string a=String.Join(" ",args), x="GPU-11111111-1111-1111-1111-111111111111", y="GPU-22222222-2222-2222-2222-222222222222";
        if(a.Contains("query-compute-apps")) {
            foreach(var p in Process.GetProcessesByName("ollama_fixture")) { Console.WriteLine(x+", "+p.Id+", 1024"); Console.WriteLine(y+", "+p.Id+", 1024"); p.Dispose(); }
        } else if(a.Contains("memory.total")) { Console.WriteLine(x+", Fixture Card A, 12288, 999.0"); Console.WriteLine(y+", Fixture Card B, 16384, 999.0"); }
        else { Console.WriteLine(x+", 1024, 0, 35, 20"); Console.WriteLine(y+", 1024, 0, 35, 20"); }
    }
}
'@
Add-Type -OutputAssembly (Join-Path $Destination 'ollama_fixture.exe') -OutputType ConsoleApplication -TypeDefinition @'
using System;
using System.IO;
using System.Text;
using System.Net;
using System.Net.Sockets;
using System.Diagnostics;
public static class FakeOllama {
    public static void Main(string[] args) {
        if(args.Length>0 && args[0]=="child") { System.Threading.Thread.Sleep(60000); return; }
        string host=Environment.GetEnvironmentVariable("OLLAMA_HOST");
        if(!host.StartsWith("127.0.0.1:") || Environment.GetEnvironmentVariable("OLLAMA_NO_CLOUD")!="1" || Environment.GetEnvironmentVariable("GGML_VK_VISIBLE_DEVICES")!="-1") return;
        var listener=new TcpListener(IPAddress.Loopback,Int32.Parse(host.Split(':')[1])); listener.Start();
        while(true) using(var client=listener.AcceptTcpClient()) using(var stream=client.GetStream()) {
            client.ReceiveTimeout=5000; client.SendTimeout=5000;
            var reader=new StreamReader(stream,Encoding.UTF8,false,1024,true);
            string start=reader.ReadLine(), line; int len=0;
            while(!String.IsNullOrEmpty(line=reader.ReadLine())) if(line.StartsWith("Content-Length:",StringComparison.OrdinalIgnoreCase)) len=Int32.Parse(line.Substring(15).Trim());
            var chars=new char[len]; int read=0; while(read<len) { int n=reader.Read(chars,read,len-read); if(n<=0) break; read+=n; }
            string body="{}";
            if(start.Contains("/api/version")) body="{\"version\":\"fixture-offline-v1\"}";
            if(start.Contains("/api/tags")) body="{\"models\":[{\"name\":\"fixture:latest\",\"digest\":\"fixture-digest\"}]}";
            if(start.Contains("/api/ps")) body="{\"models\":[{\"name\":\"fixture:latest\",\"digest\":\"fixture-digest\",\"size\":4096,\"size_vram\":2048,\"context_length\":4096}]}";
            if(start.Contains("/api/generate")) {
                var child=new ProcessStartInfo(Process.GetCurrentProcess().MainModule.FileName,"child"); child.UseShellExecute=false; child.CreateNoWindow=true; Process.Start(child).Dispose();
                body="{\"response\":\"fixture\",\"done\":false}\n{\"done\":true,\"done_reason\":\"stop\",\"load_duration\":1000,\"total_duration\":500000000,\"prompt_eval_count\":10,\"prompt_eval_duration\":100000000,\"eval_count\":32,\"eval_duration\":400000000}\n";
            }
            byte[] payload=Encoding.UTF8.GetBytes(body), header=Encoding.ASCII.GetBytes("HTTP/1.1 200 OK\r\nContent-Type: application/json\r\nContent-Length: "+payload.Length+"\r\nConnection: close\r\n\r\n");
            stream.Write(header,0,header.Length); stream.Write(payload,0,payload.Length); stream.Flush();
        }
    }
}
'@
