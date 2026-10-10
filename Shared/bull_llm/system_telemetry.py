"""Aggregate Windows inference-host telemetry, without WMI or administrator rights."""
from __future__ import annotations

import json
import math


def parse_sample(line):
    try:
        raw = str(line).strip()
        if raw.startswith('{'):
            row = json.loads(raw)
            values = [row['cpu_util'], row['ram_used_bytes'], row['ram_total_bytes']]
        else:
            fields = raw.split(',')
            if len(fields) != 3:
                return None
            values = [float(x.strip()) for x in fields]
        if any(isinstance(x, bool) or (x is not None and not isinstance(x, (int, float))) for x in values):
            return None
        cpu, used, total = values
        if used is None or total is None:
            return None
        if any(not math.isfinite(float(x)) for x in values if x is not None):
            return None
        if (cpu is not None and not 0 <= cpu <= 100) or not 0 <= used <= total or total <= 0:
            return None
        return {'cpu_util': None if cpu is None else float(cpu),
                'ram_used_bytes': float(used), 'ram_total_bytes': float(total)}
    except (ValueError, TypeError, KeyError, OverflowError):
        return None


def windows_script(interval_ms=1000):
    delay = max(500, int(interval_ms))
    # Fixed engine-owned code. No model output, paths or shell input are interpolated.
    return r'''$ErrorActionPreference='Stop'
[Console]::OutputEncoding=New-Object System.Text.UTF8Encoding($false)
Add-Type -TypeDefinition @'
using System;
using System.Runtime.InteropServices;
public static class BullHostCounters {
    [StructLayout(LayoutKind.Sequential)] public struct Memory {
        public uint length, load;
        public ulong total, available, pageTotal, pageAvailable, virtualTotal, virtualAvailable, extended;
    }
    [DllImport("kernel32.dll")] static extern bool GetSystemTimes(out long idle, out long kernel, out long user);
    [DllImport("kernel32.dll")] static extern bool GlobalMemoryStatusEx(ref Memory memory);
    static long lastIdle, lastTotal;
    public static double[] Read() {
        Memory m = new Memory(); m.length = (uint)Marshal.SizeOf(typeof(Memory));
        if (!GlobalMemoryStatusEx(ref m)) throw new Exception("memory_counter_unavailable");
        double cpu = Double.NaN;
        long idle, kernel, user;
        if (GetSystemTimes(out idle, out kernel, out user)) {
            long total = kernel + user;
            if (lastTotal != 0 && total > lastTotal)
                cpu = Math.Max(0, Math.Min(100, 100.0 * (1.0 - (double)(idle-lastIdle)/(total-lastTotal))));
            lastIdle = idle; lastTotal = total;
        }
        return new double[] {cpu, (double)(m.total-m.available), (double)m.total};
    }
}
'@
while ($true) {
    $v=[BullHostCounters]::Read()
    $cpu=$null
    if (-not [double]::IsNaN($v[0])) { $cpu=$v[0] }
    [Console]::Out.WriteLine(([ordered]@{cpu_util=$cpu; ram_used_bytes=$v[1]; ram_total_bytes=$v[2]} | ConvertTo-Json -Compress))
    [Console]::Out.Flush()
    Start-Sleep -Milliseconds ''' + str(delay) + '\n}\n'
