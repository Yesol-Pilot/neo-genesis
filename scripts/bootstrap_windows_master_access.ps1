# Neo Genesis Windows master-access bootstrap.
# Run once from the target Windows PC in an elevated PowerShell session.

$ErrorActionPreference = "Stop"

$MasterPublicKey = "ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIKxbJLkvo2ggN5kxz87XR8489VlKr0CtDxmPvSo6+Mjv yesol@DESKTOP-SOL01"

function Assert-Administrator {
    $identity = [Security.Principal.WindowsIdentity]::GetCurrent()
    $principal = New-Object Security.Principal.WindowsPrincipal($identity)
    if (-not $principal.IsInRole([Security.Principal.WindowsBuiltInRole]::Administrator)) {
        throw "Run this script from an elevated PowerShell session."
    }
}

function Add-KeyIfMissing {
    param(
        [Parameter(Mandatory = $true)][string]$Path,
        [Parameter(Mandatory = $true)][string]$Key
    )

    $dir = Split-Path -Parent $Path
    New-Item -ItemType Directory -Force -Path $dir | Out-Null

    if (-not (Test-Path -LiteralPath $Path)) {
        New-Item -ItemType File -Force -Path $Path | Out-Null
    }

    $existing = Get-Content -LiteralPath $Path -ErrorAction SilentlyContinue
    if ($existing -notcontains $Key) {
        Add-Content -LiteralPath $Path -Value $Key -Encoding ascii
    }
}

Assert-Administrator

$capability = Get-WindowsCapability -Online -Name "OpenSSH.Server~~~~0.0.1.0" -ErrorAction SilentlyContinue
if ($capability -and $capability.State -ne "Installed") {
    Add-WindowsCapability -Online -Name "OpenSSH.Server~~~~0.0.1.0" | Out-Null
}

Set-Service -Name sshd -StartupType Automatic
Start-Service -Name sshd

$userAuthorizedKeys = Join-Path $env:USERPROFILE ".ssh\authorized_keys"
Add-KeyIfMissing -Path $userAuthorizedKeys -Key $MasterPublicKey

$adminAuthorizedKeys = "C:\ProgramData\ssh\administrators_authorized_keys"
Add-KeyIfMissing -Path $adminAuthorizedKeys -Key $MasterPublicKey
icacls $adminAuthorizedKeys /inheritance:r | Out-Null
icacls $adminAuthorizedKeys /grant "Administrators:F" /grant "SYSTEM:F" | Out-Null

if (Get-Command New-NetFirewallRule -ErrorAction SilentlyContinue) {
    if (-not (Get-NetFirewallRule -Name "OpenSSH-Server-In-TCP" -ErrorAction SilentlyContinue)) {
        New-NetFirewallRule `
            -Name "OpenSSH-Server-In-TCP" `
            -DisplayName "OpenSSH Server (sshd)" `
            -Enabled True `
            -Direction Inbound `
            -Protocol TCP `
            -Action Allow `
            -LocalPort 22 | Out-Null
    } else {
        Enable-NetFirewallRule -Name "OpenSSH-Server-In-TCP" | Out-Null
    }
}

Set-ItemProperty -Path "HKLM:\System\CurrentControlSet\Control\Terminal Server" -Name "fDenyTSConnections" -Value 0
Enable-NetFirewallRule -DisplayGroup "Remote Desktop" -ErrorAction SilentlyContinue | Out-Null

Write-Output "Neo Genesis master access bootstrap complete."
Write-Output "Computer: $env:COMPUTERNAME"
Write-Output "User: $env:USERNAME"
Write-Output "OpenSSH: $((Get-Service sshd).Status)"
Write-Output "RDP fDenyTSConnections: $((Get-ItemProperty -Path 'HKLM:\System\CurrentControlSet\Control\Terminal Server' -Name fDenyTSConnections).fDenyTSConnections)"
