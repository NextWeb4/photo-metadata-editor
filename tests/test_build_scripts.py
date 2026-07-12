from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1]


class BuildScriptTests(unittest.TestCase):
    def test_msi_forces_rootdrive_to_the_local_windows_volume_before_costing(self) -> None:
        setup = (ROOT / "setup_msi.py").read_text(encoding="utf-8")

        self.assertIn('("A_SET_ROOT_DRIVE", 256 + 51, "ROOTDRIVE", "[WindowsVolume]")', setup)
        self.assertIn('("A_SET_ROOT_DRIVE", "1", 400)', setup)
        self.assertIn(
            '("A_SET_PERSONAL_FOLDER", 256 + 51, "PersonalFolder", "[LocalAppDataFolder]")',
            setup,
        )
        self.assertIn('("A_SET_PERSONAL_FOLDER", "1", 399)', setup)

    def test_msi_namespaces_generated_directory_identifiers(self) -> None:
        setup = (ROOT / "setup_msi.py").read_text(encoding="utf-8")

        self.assertIn("class BuildMsiCommand(cx_bdist_msi)", setup)
        self.assertIn('logical_name = f"PME_DIR_{digest}"', setup)
        self.assertIn('"bdist_msi": BuildMsiCommand', setup)

    def test_exe_build_rejects_reparse_output_roots_before_pyinstaller_runs(self) -> None:
        script = (ROOT / "scripts" / "build_exe.ps1").read_text(encoding="utf-8")
        pyinstaller_index = script.index("python -m PyInstaller")
        preflight_index = script.index("foreach ($OutputRoot in @($BuildRoot, $DistRoot, $PyInstallerSpecRoot))")

        self.assertIn("function Assert-UnderProject", script)
        self.assertIn("function Assert-NotReparsePoint", script)
        self.assertIn("[System.IO.FileAttributes]::ReparsePoint", script)
        self.assertIn("Refusing to use reparse point in build output", script)
        self.assertIn('$PyInstallerSpecRoot = Join-Path $BuildRoot "pyinstaller-spec"', script)
        self.assertIn('--specpath "build\\pyinstaller-spec"', script)
        self.assertIn('--add-binary "$VendorExifTool;exiftool"', script)
        self.assertIn('--add-data "$VendorExifToolFiles;exiftool\\exiftool_files"', script)
        self.assertIn('--add-data "$LicensePayload;licenses"', script)
        self.assertLess(preflight_index, pyinstaller_index)

    def test_exe_build_rechecks_the_generated_app_before_replacing_licenses(self) -> None:
        script = (ROOT / "scripts" / "build_exe.ps1").read_text(encoding="utf-8")
        replacement_index = script.index("Remove-Item -LiteralPath $ResolvedLicenseDir -Recurse -Force")

        self.assertLess(script.index("Assert-UnderProject $DistApp"), replacement_index)
        self.assertLess(script.index("Assert-NotReparsePoint $DistApp"), replacement_index)
        self.assertLess(script.index("Assert-UnderProject $RootLicenseDir"), replacement_index)
        self.assertLess(script.index("Assert-NotReparsePoint $RootLicenseDir"), replacement_index)
        self.assertLess(script.index("Assert-NoNestedReparsePoint $RootLicenseDir"), replacement_index)

    def test_msi_build_rejects_nested_reparse_points_before_recursive_delete(self) -> None:
        script = (ROOT / "scripts" / "build_msi.ps1").read_text(encoding="utf-8")
        remove_index = script.index("Remove-Item -LiteralPath $BuildRoot -Recurse -Force")

        self.assertIn("function Assert-NoNestedReparsePoint", script)
        self.assertIn("System.Collections.Generic.Stack[System.IO.DirectoryInfo]", script)
        self.assertIn("Refusing to modify nested reparse point", script)
        self.assertLess(script.index("Assert-UnderProject $BuildRoot"), remove_index)
        self.assertLess(script.index("Assert-NotReparsePoint $BuildRoot"), remove_index)
        self.assertLess(script.index("Assert-NoNestedReparsePoint $BuildRoot"), remove_index)

    def test_release_build_rejects_an_empty_or_incomplete_portable_zip_before_final_scan(self) -> None:
        script = (ROOT / "scripts" / "build_release.ps1").read_text(encoding="utf-8")
        final_scan_index = script.index("$ScanTargets = @(")
        zip_validation_index = script.index("Assert-PortableZip $PortableZip")

        self.assertIn("function Assert-PortableZip", script)
        self.assertIn("Portable ZIP is empty", script)
        self.assertIn("PhotoMetaEditor/PhotoMetaEditor.exe", script)
        self.assertIn("PhotoMetaEditor/licenses/PROJECT-LICENSE.txt", script)
        self.assertIn("PhotoMetaEditor/licenses/THIRD_PARTY.md", script)
        self.assertIn("PhotoMetaEditor/licenses/Strawberry-Perl-Licenses.zip", script)
        self.assertIn("PhotoMetaEditor/licenses/PyInstaller-COPYING.txt", script)
        self.assertIn("PhotoMetaEditor/licenses/cx_Freeze-LICENSE.md", script)
        self.assertLess(zip_validation_index, final_scan_index)

    def test_release_build_verifies_installer_creator_and_contact_metadata(self) -> None:
        script = (ROOT / "scripts" / "build_release.ps1").read_text(encoding="utf-8")
        pre_sign_scan_index = script.index("$PreSignScanTargets = @(")
        msi_validation_index = script.index("Assert-MsiMetadata $MsiPath $AppMetadata")

        self.assertIn("function Get-AppMetadata", script)
        self.assertIn("function Assert-MsiMetadata", script)
        self.assertIn("WindowsInstaller.Installer", script)
        self.assertIn('ARPCONTACT', script)
        self.assertIn('ARPURLINFOABOUT', script)
        self.assertIn("FinalReleaseComObject", script)
        self.assertIn("$View.Close()", script)
        self.assertIn("MSI Directory identifier is not namespaced", script)
        self.assertLess(msi_validation_index, pre_sign_scan_index)

    def test_release_build_verifies_actual_exe_metadata_before_signing(self) -> None:
        script = (ROOT / "scripts" / "build_release.ps1").read_text(encoding="utf-8")
        signing_index = script.index("$SignTargets = @($ExePath, $MsiPath)")
        exe_validation_index = script.index("Assert-ExeMetadata $ExePath $AppMetadata")

        self.assertIn("function Assert-ExeMetadata", script)
        self.assertIn("[Diagnostics.FileVersionInfo]::GetVersionInfo($Path)", script)
        self.assertIn("CompanyName", script)
        self.assertIn("ProductVersion", script)
        self.assertIn("Creator: $($Expected.creator); Email: $($Expected.email); Website: $($Expected.website)", script)
        self.assertLess(exe_validation_index, signing_index)

    def test_release_build_verifies_exe_and_msi_license_payloads_before_signing(self) -> None:
        script = (ROOT / "scripts" / "build_release.ps1").read_text(encoding="utf-8")
        signing_index = script.index("$SignTargets = @($ExePath, $MsiPath)")
        dist_license_index = script.index('Assert-LicensePayload (Join-Path $DistRoot "PhotoMetaEditor")')
        msi_license_index = script.index('Assert-LicensePayload (Join-Path $ProjectRoot "build\\cx_freeze\\PhotoMetaEditor")')

        self.assertIn("function Assert-LicensePayload", script)
        self.assertIn("licenses\\PROJECT-LICENSE.txt", script)
        self.assertIn("licenses\\THIRD_PARTY.md", script)
        self.assertIn("licenses\\ExifTool-Windows-README.txt", script)
        self.assertIn("licenses\\Strawberry-Perl-Licenses.zip", script)
        self.assertIn("licenses\\tkinterdnd2-LICENSE", script)
        self.assertLess(dist_license_index, signing_index)
        self.assertLess(msi_license_index, signing_index)

    def test_signing_requires_an_explicit_trusted_certificate_and_never_creates_one(self) -> None:
        script = (ROOT / "scripts" / "sign_artifacts.ps1").read_text(encoding="utf-8")
        release_script = (ROOT / "scripts" / "build_release.ps1").read_text(encoding="utf-8")

        self.assertIn("PHOTO_META_EDITOR_SIGNING_CERT_THUMBPRINT", script)
        self.assertIn("No trusted code-signing certificate thumbprint was supplied", script)
        self.assertIn('$Result.Status.ToString() -ne "Valid"', script)
        self.assertIn("$Certificate.NotBefore -gt $Now -or $Certificate.NotAfter -lt $Now", script)
        self.assertNotIn("New-SelfSignedCertificate", script)
        self.assertNotIn("SelfSignedUntrustedRoot", script)
        self.assertIn("release artifacts remain unsigned", release_script)


if __name__ == "__main__":
    unittest.main()
