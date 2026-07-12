$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$BuildRoot = Join-Path $ProjectRoot "build\cx_freeze"
$DistRoot = Join-Path $ProjectRoot "dist"

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
        throw "Refusing to modify reparse point: $Path"
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
                throw "Refusing to modify nested reparse point: $($Child.FullName)"
            }
            if ($Child.PSIsContainer) {
                $Stack.Push($Child)
            }
        }
    }
}

Push-Location $ProjectRoot
try {
    if (Test-Path -LiteralPath $BuildRoot) {
        Assert-UnderProject $BuildRoot
        Assert-NotReparsePoint $BuildRoot
        Assert-NoNestedReparsePoint $BuildRoot
        Remove-Item -LiteralPath $BuildRoot -Recurse -Force
    }
    if (Test-Path -LiteralPath $DistRoot) {
        Assert-UnderProject $DistRoot
        Assert-NotReparsePoint $DistRoot
        Get-ChildItem -LiteralPath $DistRoot -Filter "PhotoMetadataEditor-*.msi" -File | ForEach-Object {
            Assert-UnderProject $_.FullName
            Assert-NotReparsePoint $_.FullName
            Remove-Item -LiteralPath $_.FullName -Force
        }
    }
    python setup_msi.py bdist_msi
    if ($LASTEXITCODE -ne 0) {
        throw "MSI build failed with exit code $LASTEXITCODE"
    }
}
finally {
    Pop-Location
}
