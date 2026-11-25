// SPDX-License-Identifier: GPL-3.0-only
using System;
using System.ComponentModel;
using System.Diagnostics;
using System.IO;
using System.Runtime.InteropServices;
using System.Security.Cryptography;
using System.Text;
using System.Text.RegularExpressions;
using System.Threading;
using System.Windows.Forms;
using Microsoft.Win32.SafeHandles;

internal static class UpdateHandoff
{
    private const string InstallerPattern = @"\Att-tool-[0-9]{1,6}\.[0-9]{1,6}\.[0-9]{1,6}-windows-x64-setup\.exe\z";
    private const FileAttributes Reparse = FileAttributes.ReparsePoint;
    private const uint GenericWrite = 0x40000000;
    private const uint CreateAlways = 2;

    [DllImport("kernel32.dll", CharSet = CharSet.Unicode, ExactSpelling = true, SetLastError = true)]
    private static extern SafeFileHandle CreateFileW(string fileName, uint access, uint sharing,
        IntPtr security, uint disposition, uint flags, IntPtr template);

    [STAThread]
    private static int Main(string[] args)
    {
        int pid;
        long created;
        if (args.Length != 6 || !int.TryParse(args[0], out pid) || pid < 1
            || !long.TryParse(args[1], out created) || created < 1
            || !Regex.IsMatch(args[3], @"\A[a-f0-9]{64}\z"))
            return 1;

        string installer = Path.GetFullPath(args[2]);
        string directory = Path.GetDirectoryName(installer);
        string app = Path.GetFullPath(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, ".."));
        string runtime = Path.Combine(app, @"runtime\pythonw.exe");
        bool appExited = false;
        bool installed = false;
        bool usable = false;
        bool safeDownload = false;
        bool removed = false;
        try
        {
            safeDownload = IsDownload(installer, directory);
            Trace("download location valid: " + safeDownload);
            Trace("waiting for the previous app");
            WaitForApp(pid, created, runtime);
            appExited = true;
            Trace("previous app exited");
            if (!safeDownload)
                throw new IOException("The installer is outside the expected download directory.");
            installed = Install(installer, app, args[3]);
        }
        catch (Exception error)
        {
            TraceFailure(error);
            if (!ExpectedFailure(error))
                throw;
            installed = false;
        }
        finally
        {
            if (safeDownload)
                removed = Cleanup(installer, directory);
            if (appExited)
                usable = Reopen(app, runtime);
            Trace("download removed: " + removed + ", app reopened: " + usable);
        }

        if (installed && usable && removed)
            return 0;
        Trace("showing update failure dialog");
        MessageBox.Show(args[5], args[4], MessageBoxButtons.OK, MessageBoxIcon.Warning);
        return 1;
    }

    private static bool IsDownload(string installer, string directory)
    {
        string temp = Path.GetFullPath(Path.GetTempPath()).TrimEnd(Path.DirectorySeparatorChar);
        return directory != null && SamePath(Path.GetDirectoryName(directory), temp)
            && Regex.IsMatch(Path.GetFileName(directory), @"\Att-tool-update-[a-z0-9_]+\z")
            && Regex.IsMatch(Path.GetFileName(installer), InstallerPattern)
            && Directory.Exists(directory)
            && (File.GetAttributes(directory) & Reparse) == 0
            && (!File.Exists(installer) || (File.GetAttributes(installer) & Reparse) == 0);
    }

    private static bool SamePath(string first, string second)
    {
        return string.Equals(first, second, StringComparison.OrdinalIgnoreCase);
    }

    private static void WaitForApp(int pid, long created, string runtime)
    {
        Process process;
        try
        {
            process = Process.GetProcessById(pid);
        }
        catch (ArgumentException)
        {
            return;
        }

        using (process)
        {
            try
            {
                // Acquire the process handle before checking identity so PID reuse cannot change the wait target.
                if (process.Handle == IntPtr.Zero)
                    throw new InvalidOperationException("Cannot wait for the update parent.");
                if (process.StartTime.ToFileTimeUtc() != created)
                    return;
                if (!SamePath(process.MainModule.FileName, runtime))
                    throw new InvalidOperationException("The update parent is not this installation.");
                if (!process.WaitForExit(30000))
                    throw new TimeoutException("The update parent did not exit.");
            }
            catch (InvalidOperationException)
            {
                if (!process.HasExited)
                    throw;
            }
            catch (Win32Exception)
            {
                if (!process.HasExited)
                    throw;
            }
        }
    }

    private static bool Install(string installer, string app, string expectedDigest)
    {
        using (FileStream locked = File.Open(installer, FileMode.Open, FileAccess.Read, FileShare.Read))
        using (SHA256 sha256 = SHA256.Create())
        {
            string digest = BitConverter.ToString(sha256.ComputeHash(locked)).Replace("-", "").ToLowerInvariant();
            if (!string.Equals(digest, expectedDigest, StringComparison.Ordinal))
            {
                Trace("download digest mismatch");
                return false;
            }
            Trace("download digest verified");
            MarkAsDownload(installer);

            var settings = new ProcessStartInfo(installer)
            {
                // Let Inno Setup reuse the installed language and selected shortcut tasks.
                Arguments = "/SP- /SILENT /SUPPRESSMSGBOXES /NORESTART /RESTARTEXITCODE=9 "
                    + "/NOCLOSEAPPLICATIONS /NORESTARTAPPLICATIONS /DIR=\"" + app + "\"",
                UseShellExecute = true,
                WorkingDirectory = Path.GetDirectoryName(installer)
            };
            Trace("opening marked installer with Windows ShellExecute");
            using (Process setup = Process.Start(settings))
            {
                if (setup == null)
                    return false;
                Trace("setup process started (PID " + setup.Id + ")");
                setup.WaitForExit();
                Trace("setup exited with code " + setup.ExitCode);
                return setup.ExitCode == 0;
            }
        }
    }

    private static void MarkAsDownload(string installer)
    {
        // .NET Framework path validation rejects Windows alternate data streams.
        using (SafeFileHandle handle = CreateFileW(installer + ":Zone.Identifier", GenericWrite, 0,
            IntPtr.Zero, CreateAlways, 0, IntPtr.Zero))
        {
            if (handle.IsInvalid)
                throw new Win32Exception(Marshal.GetLastWin32Error());
            byte[] marker = Encoding.ASCII.GetBytes("[ZoneTransfer]\r\nZoneId=3\r\n");
            using (var stream = new FileStream(handle, FileAccess.Write))
                stream.Write(marker, 0, marker.Length);
        }
    }

    private static bool Reopen(string app, string runtime)
    {
        var settings = new ProcessStartInfo(runtime)
        {
            Arguments = "-I -B \"" + Path.Combine(app, @"app\tt_tool_launcher.py") + "\"",
            WorkingDirectory = app,
            UseShellExecute = false
        };
        try
        {
            using (Process reopened = Process.Start(settings))
                return reopened != null;
        }
        catch (Exception error)
        {
            TraceFailure(error);
            if (!ExpectedFailure(error))
                throw;
            return false;
        }
    }

    private static void Trace(string message)
    {
        try
        {
            if (Console.IsOutputRedirected)
                Console.WriteLine("tt tool update: " + message);
        }
        catch (IOException)
        {
            // A closed diagnostic sink must not affect the update.
        }
    }

    private static void TraceFailure(Exception error)
    {
        var native = error as Win32Exception;
        string location = error.TargetSite == null ? "unknown" : error.TargetSite.Name;
        string code = native == null ? error.HResult.ToString("X8") : native.NativeErrorCode.ToString();
        Trace("failure in " + location + ": " + error.GetType().Name + " (" + code + ")");
    }

    private static bool ExpectedFailure(Exception error)
    {
        return error is IOException || error is UnauthorizedAccessException || error is Win32Exception
            || error is TimeoutException || error is InvalidOperationException || error is CryptographicException;
    }

    private static bool Cleanup(string installer, string directory)
    {
        for (int attempt = 0; attempt < 5; attempt++)
        {
            try
            {
                File.Delete(installer);
                if (Directory.Exists(directory))
                    Directory.Delete(directory, false);
                return true;
            }
            catch (Exception error)
            {
                if (!(error is IOException || error is UnauthorizedAccessException))
                    throw;
                Thread.Sleep(200);
            }
        }
        return false;
    }
}
