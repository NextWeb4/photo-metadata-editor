$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$DistRoot = Join-Path $ProjectRoot "dist"
$PortableZip = Join-Path $DistRoot "PhotoMetaEditor-portable.zip"
$ExePath = Join-Path $DistRoot "PhotoMetaEditor\PhotoMetaEditor.exe"

function Invoke-Checked {
    param(
        [Parameter(Mandatory=$true)]
        [scriptblock] $Command,
        [Parameter(Mandatory=$true)]
        [string] $Name
    )
    & $Command
    if ($LASTEXITCODE -ne 0) {
        throw "$Name failed with exit code $LASTEXITCODE"
    }
}

function Assert-PortableZip {
    param([Parameter(Mandatory=$true)][string] $Path)

    if (-not (Test-Path -LiteralPath $Path)) {
        throw "Portable ZIP was not created: $Path"
    }
    if ((Get-Item -LiteralPath $Path).Length -le 0) {
        throw "Portable ZIP is empty: $Path"
    }

    Add-Type -AssemblyName System.IO.Compression.FileSystem
    $Archive = $null
    try {
        $Archive = [System.IO.Compression.ZipFile]::OpenRead($Path)
        $EntryNames = @($Archive.Entries | ForEach-Object { $_.FullName.Replace('\', '/') })
        foreach ($RequiredEntry in @(
            "PhotoMetaEditor/PhotoMetaEditor.exe",
        "PhotoMetaEditor/licenses/PROJECT-LICENSE.txt",
        "PhotoMetaEditor/licenses/THIRD_PARTY.md",
        "PhotoMetaEditor/licenses/ExifTool-Windows-LICENSE.txt",
        "PhotoMetaEditor/licenses/Strawberry-Perl-Licenses.zip",
        "PhotoMetaEditor/licenses/PyInstaller-COPYING.txt",
        "PhotoMetaEditor/licenses/cx_Freeze-LICENSE.md",
        "PhotoMetaEditor/licenses/tkinterdnd2-LICENSE"
        )) {
            if ($EntryNames -notcontains $RequiredEntry) {
                throw "Portable ZIP is missing required entry: $RequiredEntry"
            }
        }
    }
    finally {
        if ($Archive) {
            $Archive.Dispose()
        }
    }
}

function Assert-LicensePayload {
    param([Parameter(Mandatory=$true)][string] $Path)

    if (-not (Test-Path -LiteralPath $Path -PathType Container)) {
        throw "License payload root is missing: $Path"
    }
    foreach ($RequiredFile in @(
        "licenses\PROJECT-LICENSE.txt",
        "licenses\THIRD_PARTY.md",
        "licenses\ExifTool-Windows-LICENSE.txt",
        "licenses\ExifTool-Windows-README.txt",
        "licenses\Strawberry-Perl-Licenses.zip",
        "licenses\PyInstaller-COPYING.txt",
        "licenses\cx_Freeze-LICENSE.md",
        "licenses\tkinterdnd2-LICENSE"
    )) {
        $Candidate = Join-Path $Path $RequiredFile
        if (-not (Test-Path -LiteralPath $Candidate -PathType Leaf)) {
            throw "License payload is missing required file: $Candidate"
        }
    }
}

function Get-AppMetadata {
    $MetadataJson = python -c "import json, sys; sys.path.insert(0, 'src'); from photo_meta_editor.metadata import APP_COPYRIGHT, APP_CREATOR, APP_EMAIL, APP_NAME, APP_VERSION, APP_WEBSITE; print(json.dumps({'creator': APP_CREATOR, 'email': APP_EMAIL, 'website': APP_WEBSITE, 'name': APP_NAME, 'version': APP_VERSION, 'copyright': APP_COPYRIGHT}))"
    if ($LASTEXITCODE -ne 0) {
        throw "Application metadata lookup failed with exit code $LASTEXITCODE"
    }
    return $MetadataJson | ConvertFrom-Json
}

function Assert-ExeMetadata {
    param(
        [Parameter(Mandatory=$true)][string] $Path,
        [Parameter(Mandatory=$true)]$Expected
    )

    if (-not (Test-Path -LiteralPath $Path -PathType Leaf)) {
        throw "EXE was not created: $Path"
    }
    $Info = [Diagnostics.FileVersionInfo]::GetVersionInfo($Path)
    $VersionParts = @($Expected.version.Split("."))
    while ($VersionParts.Count -lt 4) {
        $VersionParts += "0"
    }
    $ExpectedVersion = ($VersionParts[0..3] -join ".")
    $ExpectedComments = "Creator: $($Expected.creator); Email: $($Expected.email); Website: $($Expected.website)"
    $Checks = @(
        @{ Label = "CompanyName"; Actual = $Info.CompanyName; Expected = $Expected.creator },
        @{ Label = "FileDescription"; Actual = $Info.FileDescription; Expected = $Expected.name },
        @{ Label = "ProductName"; Actual = $Info.ProductName; Expected = $Expected.name },
        @{ Label = "FileVersion"; Actual = $Info.FileVersion; Expected = $ExpectedVersion },
        @{ Label = "ProductVersion"; Actual = $Info.ProductVersion; Expected = $ExpectedVersion },
        @{ Label = "LegalCopyright"; Actual = $Info.LegalCopyright; Expected = $Expected.copyright },
        @{ Label = "Comments"; Actual = $Info.Comments; Expected = $ExpectedComments }
    )
    foreach ($Check in $Checks) {
        if ($Check.Actual -ne $Check.Expected) {
            throw "EXE $($Check.Label) mismatch: expected '$($Check.Expected)', got '$($Check.Actual)'"
        }
    }
}

function Assert-MsiMetadata {
    param(
        [Parameter(Mandatory=$true)][string] $Path,
        [Parameter(Mandatory=$true)]$Expected
    )

    $Installer = $null
    $Database = $null
    $View = $null
    $DirectoryView = $null
    $Summary = $null
    try {
        try {
            $Installer = New-Object -ComObject WindowsInstaller.Installer
            $Database = $Installer.OpenDatabase($Path, 0)
            $Backtick = [char]96
            $View = $Database.OpenView(('SELECT {0}Property{0}, {0}Value{0} FROM {0}Property{0}' -f $Backtick))
            $View.Execute()
            $Properties = @{}
            while ($Record = $View.Fetch()) {
                $Properties[$Record.StringData(1)] = $Record.StringData(2)
            }
            $DirectoryView = $Database.OpenView(('SELECT {0}Directory{0} FROM {0}Directory{0}' -f $Backtick))
            $DirectoryView.Execute()
            while ($DirectoryRecord = $DirectoryView.Fetch()) {
                $DirectoryId = $DirectoryRecord.StringData(1)
                if ($DirectoryId -ne "TARGETDIR" -and $DirectoryId -notmatch '^PME_DIR_[0-9a-f]{24}$') {
                    throw "MSI Directory identifier is not namespaced: $DirectoryId"
                }
            }
            $Summary = $Database.SummaryInformation(0)
        }
        catch {
            throw "Unable to inspect MSI metadata: $($_.Exception.Message)"
        }

        $ExpectedContact = "$($Expected.creator) <$($Expected.email)>"
        $ExpectedComments = "Email: $($Expected.email); Website: $($Expected.website)"
        $Checks = @(
            @{ Label = "Manufacturer"; Actual = $Properties["Manufacturer"]; Expected = $Expected.creator },
            @{ Label = "ARPCONTACT"; Actual = $Properties["ARPCONTACT"]; Expected = $ExpectedContact },
            @{ Label = "ARPURLINFOABOUT"; Actual = $Properties["ARPURLINFOABOUT"]; Expected = $Expected.website },
            @{ Label = "Summary author"; Actual = $Summary.Property(4); Expected = $Expected.creator },
            @{ Label = "Summary comments"; Actual = $Summary.Property(6); Expected = $ExpectedComments }
        )
        foreach ($Check in $Checks) {
            if ($Check.Actual -ne $Check.Expected) {
                throw "MSI $($Check.Label) mismatch: expected '$($Check.Expected)', got '$($Check.Actual)'"
            }
        }
    }
    finally {
        if ($View) {
            try { $View.Close() } catch {}
        }
        if ($DirectoryView) {
            try { $DirectoryView.Close() } catch {}
        }
        foreach ($ComObject in @($Summary, $DirectoryView, $View, $Database, $Installer)) {
            if ($ComObject) {
                try { [void][Runtime.InteropServices.Marshal]::FinalReleaseComObject($ComObject) } catch {}
            }
        }
    }
}

Push-Location $ProjectRoot
try {
    $env:PYTHONPATH = "src"
    Invoke-Checked { python -m compileall src tests scripts setup_msi.py } "compileall"
    Invoke-Checked { python -m unittest discover -s tests } "unit tests"

    Invoke-Checked { powershell -ExecutionPolicy Bypass -File .\scripts\build_exe.ps1 } "EXE build"
    Invoke-Checked { powershell -ExecutionPolicy Bypass -File .\scripts\build_msi.ps1 } "MSI build"

    $UnexpectedMsiFiles = @(Get-ChildItem -LiteralPath $DistRoot -Filter "*.msi" -File | Where-Object { $_.Name -notlike "PhotoMetadataEditor-*.msi" })
    if ($UnexpectedMsiFiles.Count -gt 0) {
        $Names = ($UnexpectedMsiFiles | ForEach-Object { $_.FullName }) -join ", "
        throw "Unexpected MSI files in dist; refusing to publish stale or unrelated installers: $Names"
    }
    $MsiFiles = @(Get-ChildItem -LiteralPath $DistRoot -Filter "PhotoMetadataEditor-*.msi" -File)
    if ($MsiFiles.Count -ne 1) {
        throw "Expected exactly one PhotoMetadataEditor MSI, found $($MsiFiles.Count)"
    }
    $MsiPath = $MsiFiles[0].FullName
    $AppMetadata = Get-AppMetadata
    Assert-MsiMetadata $MsiPath $AppMetadata
    Assert-ExeMetadata $ExePath $AppMetadata
    Assert-LicensePayload (Join-Path $DistRoot "PhotoMetaEditor")
    Assert-LicensePayload (Join-Path $ProjectRoot "build\cx_freeze\PhotoMetaEditor")

    $PreSignScanTargets = @(
        (Join-Path $DistRoot "PhotoMetaEditor"),
        (Join-Path $ProjectRoot "build\cx_freeze\PhotoMetaEditor"),
        $MsiPath
    )
    Invoke-Checked { python scripts\check_package_privacy.py @PreSignScanTargets } "pre-sign privacy scan"

    $SignTargets = @($ExePath, $MsiPath)
    $SigningThumbprint = $env:PHOTO_META_EDITOR_SIGNING_CERT_THUMBPRINT
    if ($SigningThumbprint) {
        Invoke-Checked {
            & .\scripts\sign_artifacts.ps1 -Path $SignTargets -CertificateThumbprint $SigningThumbprint
        } "artifact signing"
    }
    else {
        Write-Host "No trusted code-signing certificate was supplied; release artifacts remain unsigned."
    }

    if (Test-Path -LiteralPath $PortableZip) {
        Remove-Item -LiteralPath $PortableZip -Force
    }
    Compress-Archive -Path (Join-Path $DistRoot "PhotoMetaEditor") -DestinationPath $PortableZip -CompressionLevel Optimal
    Assert-PortableZip $PortableZip

    $ScanTargets = @(
        (Join-Path $DistRoot "PhotoMetaEditor"),
        (Join-Path $ProjectRoot "build\cx_freeze\PhotoMetaEditor"),
        $PortableZip,
        $MsiPath
    )
    Invoke-Checked { python scripts\check_package_privacy.py @ScanTargets } "privacy scan"
}
finally {
    Pop-Location
}
