$ErrorActionPreference = 'Stop'
$desktopFolder = [Environment]::GetFolderPath('Desktop')
if (-not $desktopFolder) { throw 'Windows Desktop folder unavailable.' }
$commandName = -join ([char[]](0x66F4, 0x65B0, 0x8BBA, 0x6587))
$shortcutName = -join ([char[]](0x8BBA, 0x6587, 0x66F4, 0x65B0))
$targetPath = Join-Path $PSScriptRoot ($commandName + '.cmd')
if (-not (Test-Path -LiteralPath $targetPath)) { throw 'Update command missing.' }
$linkPath = Join-Path $desktopFolder ($shortcutName + '.lnk')
$shell = New-Object -ComObject WScript.Shell
$link = $shell.CreateShortcut($linkPath)
if ((Test-Path -LiteralPath $linkPath) -and $link.TargetPath -and $link.TargetPath -ne $targetPath) {
    throw 'A shortcut with this name already points to another program.'
}
$link.TargetPath = $targetPath
$link.WorkingDirectory = $PSScriptRoot
$link.Description = 'Update personal papers and open the reading page'
$link.Save()
$verified = $shell.CreateShortcut($linkPath)
if ($verified.TargetPath -ne $targetPath) { throw 'Shortcut verification failed.' }
Write-Output "Shortcut created and verified: $linkPath"
