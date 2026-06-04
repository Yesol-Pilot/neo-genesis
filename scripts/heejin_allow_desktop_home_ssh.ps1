# One-shot SSH access grant for desktop-home -> heejin.
# Run in an elevated PowerShell window on heejin.

$ErrorActionPreference = "Stop"
$Key = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKxbJLkvo2ggN5kxz87XR8489VlKr0CtDxmPvSo6+Mjv yesol@DESKTOP-SOL01"

function Add-Key {
    param([string]$Path)
    $dir = Split-Path -Parent $Path
    New-Item -ItemType Directory -Force -Path $dir | Out-Null
    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType File -Force -Path $Path | Out-Null
    }
    $content = Get-Content -LiteralPath $Path -ErrorAction SilentlyContinue
    if ($content -notcontains $Key) {
        Add-Content -LiteralPath $Path -Value $Key -Encoding ascii
    }
}

$isAdmin = ([Security.Principal.WindowsPrincipal] [Security.Principal.WindowsIdentity]::GetCurrent()).IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)
Write-Output "ADMIN=$isAdmin"
Write-Output "USER=$env:USERNAME"
Write-Output "USERPROFILE=$env:USERPROFILE"

Add-Key -Path (Join-Path $env:USERPROFILE ".ssh\authorized_keys")

if ($isAdmin) {
    Add-Key -Path "C:\ProgramData\ssh\administrators_authorized_keys"
    icacls "C:\ProgramData\ssh\administrators_authorized_keys" /inheritance:r | Out-Null
    icacls "C:\ProgramData\ssh\administrators_authorized_keys" /grant "Administrators:F" /grant "SYSTEM:F" | Out-Null

    Set-Service -Name sshd -StartupType Automatic
    Start-Service -Name sshd -ErrorAction SilentlyContinue

    if (Get-Command New-NetFirewallRule -ErrorAction SilentlyContinue) {
        if (-not (Get-NetFirewallRule -Name "OpenSSH-Server-In-TCP" -ErrorAction SilentlyContinue)) {
            New-NetFirewallRule -Name "OpenSSH-Server-In-TCP" -DisplayName "OpenSSH Server (sshd)" -Enabled True -Direction Inbound -Protocol TCP -Action Allow -LocalPort 22 | Out-Null
        } else {
            Enable-NetFirewallRule -Name "OpenSSH-Server-In-TCP" | Out-Null
        }
    }
}

Write-Output "SSH key grant complete."
