// Shared, portable entrypoint for Setup and BULL. No elevation, downloads or settings writes.
using System;
using System.Diagnostics;
using System.IO;
using System.Windows.Forms;
using System.Reflection;
#if SETUP
[assembly: AssemblyTitle("BULL Setup")]
[assembly: AssemblyDescription("Start here to set up BULL")]
#else
[assembly: AssemblyTitle("BULL")]
[assembly: AssemblyDescription("BULL Benchmark Lab")]
#endif
[assembly: AssemblyVersion("0.29.0.1")]

internal static class BullLauncher
{
    // Win32 argv quoting, not shell interpolation. Roots containing spaces/Unicode are valid.
    private static string Quote(string value)
    {
        // Fixed file paths (never a trailing separator) and fixed titles only.
        if (value.IndexOf('"') >= 0) throw new ArgumentException("Invalid path");
        return "\"" + value + "\"";
    }

    [STAThread]
    private static int Main(string[] args)
    {
        string root = AppDomain.CurrentDomain.BaseDirectory;
#if SETUP
        string script = Path.Combine(root, "Setup.ps1");
        string title = "BULL Setup";
#else
        string script = Path.Combine(root, "BULL-v0.29.0.1.ps1");
        string title = "BULL";
#endif
        if (args.Length == 1 && args[0] == "--self-test")
            return File.Exists(script) ? 0 : 2;
        if (args.Length != 0 || !File.Exists(script))
        {
            MessageBox.Show("Extract the complete BULL ZIP before starting / Распакуйте весь архив BULL.", title);
            return 2;
        }
        string powershell = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.System),
                                         "WindowsPowerShell", "v1.0", "powershell.exe");
        string command = "-NoLogo -NoProfile -ExecutionPolicy Bypass -File " + Quote(script);
#if SETUP
        command += " -InstallDependencies";
#endif
        string terminal = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.LocalApplicationData),
                                       "Microsoft", "WindowsApps", "wt.exe");
        // WT treats semicolons as command separators. Fall back for such paths.
        if (File.Exists(terminal) && root.IndexOf(';') < 0)
        {
            try
            {
                // Both roles use the SAME default Terminal profile, fresh window and cell size.
                Process.Start(new ProcessStartInfo(terminal,
                    "--window new --size 120,52 new-tab --title " + Quote(title) + " " +
                    Quote(powershell) + " " + command) {
                        WorkingDirectory = Environment.GetFolderPath(Environment.SpecialFolder.System),
                        UseShellExecute = false });
                return 0;
            }
            catch (System.ComponentModel.Win32Exception) { }
        }
        try
        {
            Process.Start(new ProcessStartInfo(powershell, command) {
                WorkingDirectory = root, UseShellExecute = true, WindowStyle = ProcessWindowStyle.Normal });
            return 0;
        }
        catch (Exception)
        {
            MessageBox.Show("Cannot start BULL. Try Setup.cmd / Не удалось запустить BULL. Попробуйте Setup.cmd.", title);
            return 2;
        }
    }
}
