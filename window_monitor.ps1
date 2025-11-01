# Window Change Monitor for PowerShell
# This script detects when the active window changes and prints information about it

Write-Host "Window Monitor Started" -ForegroundColor Green
Write-Host "Monitoring for window changes... (Press Ctrl+C to stop)" -ForegroundColor Yellow
Write-Host "----------------------------------------"

# Add Windows API signatures
Add-Type @"
    using System;
    using System.Runtime.InteropServices;
    using System.Text;
    
    public class WindowAPI {
        [DllImport("user32.dll")]
        public static extern IntPtr GetForegroundWindow();
        
        [DllImport("user32.dll")]
        public static extern int GetWindowText(IntPtr hWnd, StringBuilder text, int count);
        
        [DllImport("user32.dll")]
        public static extern uint GetWindowThreadProcessId(IntPtr hWnd, out uint processId);
        
        [DllImport("user32.dll")]
        public static extern int GetClassName(IntPtr hWnd, StringBuilder lpClassName, int nMaxCount);
    }
"@

# Function to get active window information
function Get-ActiveWindowInfo {
    $handle = [WindowAPI]::GetForegroundWindow()
    
    # Get window title
    $title = New-Object System.Text.StringBuilder 256
    [void][WindowAPI]::GetWindowText($handle, $title, $title.Capacity)
    
    # Get window class name
    $className = New-Object System.Text.StringBuilder 256
    [void][WindowAPI]::GetClassName($handle, $className, $className.Capacity)
    
    # Get process ID
    $processId = 0
    [void][WindowAPI]::GetWindowThreadProcessId($handle, [ref]$processId)
    
    # Get process name if possible
    $processName = ""
    try {
        $process = Get-Process -Id $processId -ErrorAction SilentlyContinue
        if ($process) {
            $processName = $process.ProcessName
        }
    } catch {
        $processName = "Unknown"
    }
    
    return @{
        Handle = $handle.ToInt64()
        Title = $title.ToString()
        ClassName = $className.ToString()
        ProcessId = $processId
        ProcessName = $processName
    }
}

# Function to print window information
function Print-WindowInfo {
    param (
        [hashtable]$WindowInfo,
        [string]$Event = "Window Changed!"
    )
    
    $timestamp = Get-Date -Format "yyyy-MM-dd HH:mm:ss"
    Write-Host "[$timestamp] $Event" -ForegroundColor Cyan
    Write-Host "  Window Handle: $($WindowInfo.Handle)" -ForegroundColor White
    Write-Host "  Title: $($WindowInfo.Title)" -ForegroundColor White
    Write-Host "  Class: $($WindowInfo.ClassName)" -ForegroundColor White
    Write-Host "  Process ID: $($WindowInfo.ProcessId)" -ForegroundColor White
    Write-Host "  Process Name: $($WindowInfo.ProcessName)" -ForegroundColor White
    Write-Host "----------------------------------------"
}

# Get initial window information
$previousWindow = Get-ActiveWindowInfo
Print-WindowInfo -WindowInfo $previousWindow -Event "Initial Window:"

# Continuous monitoring loop
try {
    while ($true) {
        # Get current active window
        $currentWindow = Get-ActiveWindowInfo
        
        # Check if window has changed
        if ($currentWindow.Handle -ne $previousWindow.Handle) {
            # Print window change notification
            Print-WindowInfo -WindowInfo $currentWindow
            
            # Update previous window
            $previousWindow = $currentWindow
        }
        
        # Small delay to prevent excessive CPU usage
        Start-Sleep -Milliseconds 500
    }
} catch {
    Write-Host "`nMonitoring stopped." -ForegroundColor Red
}
