$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$VendorExifTool = Join-Path $ProjectRoot "vendor\exiftool\exiftool.exe"
$VendorExifToolFiles = Join-Path $ProjectRoot "vendor\exiftool\exiftool_files"
$VersionInfo = Join-Path $ProjectRoot "scripts\windows_version_info.txt"
$BuildRoot = Join-Path $ProjectRoot "build"
$DistRoot = Join-Path $ProjectRoot "dist"
$PyInstallerSpecRoot = Join-Path $BuildRoot "pyinstaller-spec"
$SourceRoot = Join-Path $ProjectRoot "src"
$LicensePayload = Join-Path $BuildRoot "licenses"
$MainEntrypoint = Join-Path $SourceRoot "photo_meta_editor\__main__.py"

function Assert-UnderProject {
    param([string] $Path)
    $Resolved = Resolve-Path -LiteralPath $Path -ErrorAction SilentlyContinue
    $ProjectRootPrefix = $ProjectRoot.Path.TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
    if ($Resolved -and $Resolved.Path -ne $ProjectRoot.Path -and -not $Resolved.Path.StartsWith($ProjectRootPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
        throw "Refusing to modify path outside project: $($Resolved.Path)"
    }
}

function Assert-NotReparsePoint {
    param([string] $Path)
    $Item = Get-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
    if ($Item -and ($Item.Attributes -band [System.IO.FileAttributes]::ReparsePoint)) {
        throw "Refusing to use reparse point in build output: $Path"
    }
}

function Assert-NoNestedReparsePoint {
    param([string] $Path)
    $Root = Get-Item -LiteralPath $Path -Force -ErrorAction SilentlyContinue
    if (-not $Root -or -not $Root.PSIsContainer) {
        return
    }
    $Stack = New-Object 'System.Collections.Generic.Stack[System.IO.DirectoryInfo]'
    $Stack.Push($Root)
    while ($Stack.Count -gt 0) {
        $Directory = $Stack.Pop()
        foreach ($Child in Get-ChildItem -LiteralPath $Directory.FullName -Force -ErrorAction Stop) {
            if ($Child.Attributes -band [System.IO.FileAttributes]::ReparsePoint) {
                throw "Refusing to use nested reparse point in build output: $($Child.FullName)"
            }
            if ($Child.PSIsContainer) {
                $Stack.Push($Child)
            }
        }
    }
}

if (-not (Test-Path -LiteralPath $VendorExifTool)) {
    throw "Missing vendor\exiftool\exiftool.exe"
}

if (-not (Test-Path -LiteralPath $VendorExifToolFiles)) {
    throw "Missing vendor\exiftool\exiftool_files"
}

foreach ($OutputRoot in @($BuildRoot, $DistRoot, $PyInstallerSpecRoot)) {
    if (Test-Path -LiteralPath $OutputRoot) {
        Assert-UnderProject $OutputRoot
        Assert-NotReparsePoint $OutputRoot
        Assert-NoNestedReparsePoint $OutputRoot
    }
}

Push-Location $ProjectRoot
try {
    python .\scripts\generate_windows_version_info.py
    if ($LASTEXITCODE -ne 0) {
        throw "Windows version info generation failed with exit code $LASTEXITCODE"
    }
    if (-not (Test-Path -LiteralPath $VersionInfo)) {
        throw "Missing generated scripts\windows_version_info.txt"
    }
    python .\scripts\collect_licenses.py
    if ($LASTEXITCODE -ne 0) {
        throw "License collection failed with exit code $LASTEXITCODE"
    }
    python -m PyInstaller `
        --noconfirm `
        --clean `
        --onedir `
        --windowed `
        --name PhotoMetaEditor `
        --specpath "build\pyinstaller-spec" `
        --version-file $VersionInfo `
        --paths $SourceRoot `
        --exclude-module paddleocr `
        --exclude-module paddle `
        --exclude-module torch `
        --exclude-module torchvision `
        --exclude-module easyocr `
        --exclude-module winsdk `
        --exclude-module cv2 `
        --exclude-module scipy `
        --exclude-module pandas `
        --exclude-module matplotlib `
        --add-binary "$VendorExifTool;exiftool" `
        --add-data "$VendorExifToolFiles;exiftool\exiftool_files" `
        --add-data "$LicensePayload;licenses" `
        $MainEntrypoint
    if ($LASTEXITCODE -ne 0) {
        throw "PyInstaller failed with exit code $LASTEXITCODE"
    }
    python .\scripts\prune_runtime_payload.py .\dist\PhotoMetaEditor
    if ($LASTEXITCODE -ne 0) {
        throw "Runtime payload pruning failed with exit code $LASTEXITCODE"
    }
    $DistApp = Join-Path $ProjectRoot "dist\PhotoMetaEditor"
    $RootLicenseDir = Join-Path $DistApp "licenses"
    Assert-UnderProject $DistApp
    Assert-NotReparsePoint $DistApp
    $ResolvedDistApp = Resolve-Path -LiteralPath $DistApp
    if (Test-Path -LiteralPath $RootLicenseDir) {
        Assert-UnderProject $RootLicenseDir
        Assert-NotReparsePoint $RootLicenseDir
        Assert-NoNestedReparsePoint $RootLicenseDir
        $ResolvedLicenseDir = Resolve-Path -LiteralPath $RootLicenseDir
        $DistAppPrefix = $ResolvedDistApp.Path.TrimEnd('\', '/') + [System.IO.Path]::DirectorySeparatorChar
        if ($ResolvedLicenseDir.Path -ne $ResolvedDistApp.Path -and -not $ResolvedLicenseDir.Path.StartsWith($DistAppPrefix, [System.StringComparison]::OrdinalIgnoreCase)) {
            throw "Refusing to replace licenses outside dist app directory: $($ResolvedLicenseDir.Path)"
        }
        Remove-Item -LiteralPath $ResolvedLicenseDir -Recurse -Force
    }
    Copy-Item -LiteralPath (Join-Path $ProjectRoot "build\licenses") -Destination $DistApp -Recurse -Force
}
finally {
    Pop-Location
}
