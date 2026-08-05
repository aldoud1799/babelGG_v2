# BabelGG Installer Smoke Test Checklist

Use this checklist after generating `installer/BabelGG_Setup.exe`.

## Test Environment

- Windows machine/VM with no previous BabelGG install.
- Optional: no model folders under app install location.

## Install Validation

1. Run `BabelGG_Setup.exe` as administrator.
2. Confirm installer completes with no error dialogs.
3. Verify shortcuts created:
   - Start Menu: BabelGG
   - Desktop: BabelGG
4. Confirm install path contains `BabelGG.exe`.

## First Launch Validation

1. Launch BabelGG from Start Menu shortcut.
2. Confirm app starts and system tray icon appears.
3. On first run with missing model assets, confirm downloader dialog appears.
4. Allow model download and wait for completion.
5. Confirm main app remains responsive after download.

## Core Runtime Validation

1. Copy a known foreign-language sentence.
2. Confirm translation card appears.
3. Trigger reply flow with `Ctrl+Shift+R` (or fallback hotkey).
4. Confirm translation cache behaves normally (no crashes/hangs).

## Uninstall Validation

1. Uninstall BabelGG from Windows Apps/Programs.
2. Confirm app files are removed from install directory.
3. Confirm shortcuts are removed.

## Pass Criteria

- Install, first launch, translation flow, and uninstall all succeed.
- No blocking errors, crashes, or missing-executable failures.
