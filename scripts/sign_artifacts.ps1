param(
    [string[]] $Path,
    [string] $CertificateThumbprint = $env:PHOTO_META_EDITOR_SIGNING_CERT_THUMBPRINT
)

$ErrorActionPreference = "Stop"

$ProjectRoot = Resolve-Path (Join-Path $PSScriptRoot "..")
$ExpectedSubject = "CN=HaoXiang Huang"

if (-not $CertificateThumbprint) {
    throw "No trusted code-signing certificate thumbprint was supplied. Artifacts were not signed."
}

$NormalizedThumbprint = $CertificateThumbprint.Replace(" ", "").ToUpperInvariant()
$CertificatePath = "Cert:\CurrentUser\My\$NormalizedThumbprint"
$Certificate = Get-Item -LiteralPath $CertificatePath -ErrorAction SilentlyContinue
if (-not $Certificate) {
    throw "Code-signing certificate was not found: $NormalizedThumbprint"
}
if (-not $Certificate.HasPrivateKey) {
    throw "Code-signing certificate has no private key: $NormalizedThumbprint"
}
if ($Certificate.Subject -ne $ExpectedSubject) {
    throw "Certificate subject is '$($Certificate.Subject)', expected '$ExpectedSubject'."
}
$Now = Get-Date
if ($Certificate.NotBefore -gt $Now -or $Certificate.NotAfter -lt $Now) {
    throw "Code-signing certificate is not currently valid."
}

if (-not $Path -or $Path.Count -eq 0) {
    $Path = @(Join-Path $ProjectRoot "dist\PhotoMetaEditor\PhotoMetaEditor.exe")
    $Path += @(Get-ChildItem -LiteralPath (Join-Path $ProjectRoot "dist") -Filter "*.msi" -File -ErrorAction SilentlyContinue | ForEach-Object FullName)
}

$VerifiedResults = foreach ($Item in $Path) {
    $Resolved = Resolve-Path -LiteralPath $Item
    $Result = Set-AuthenticodeSignature -FilePath $Resolved -Certificate $Certificate -HashAlgorithm SHA256
    if ($Result.Status.ToString() -ne "Valid") {
        throw "$Resolved signature status is $($Result.Status): $($Result.StatusMessage)"
    }
    if (-not $Result.SignerCertificate -or $Result.SignerCertificate.Thumbprint -ne $Certificate.Thumbprint) {
        throw "$Resolved was not signed by the requested certificate."
    }
    [pscustomobject]@{
        Path = $Result.Path
        Status = $Result.Status.ToString()
        SignerSubject = $Result.SignerCertificate.Subject
        Thumbprint = $Result.SignerCertificate.Thumbprint
    }
}

$VerifiedResults | Format-List
