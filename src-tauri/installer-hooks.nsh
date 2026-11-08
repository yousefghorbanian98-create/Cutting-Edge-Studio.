; Cutting Edge v2 - staged Windows installer hooks
; ---------------------------------------------------------------------------
; Hooked into Tauri's generated installer.nsi through
; bundle.windows.nsis.installerHooks. Tauri includes this file at global scope
; after MUI2.nsh, FileFunc.nsh, x64.nsh and WordFunc.nsh, so those are already
; available here.
;
; Design rules this file obeys:
;   * LOCK-05 / README "no CDN or automatic downloads": prerequisites are
;     EMBEDDED at build time. Nothing is ever fetched from the network at
;     install time. If a prerequisite was not bundled, we say so and continue
;     rather than silently reaching for the internet.
;   * No duplication of what Tauri already does. Tauri owns WebView2
;     installation (bundle.windows.webviewInstallMode), file copying,
;     shortcuts, registry keys and the uninstaller. We only add the preflight
;     gate before it and the verification pass after it.
;   * Every stage reports into the single INSTFILES details view, so the user
;     sees one continuous progress report instead of separate dialogs.

!include WinVer.nsh   ; include-guarded upstream; needed for ${AtLeastWin10}

!define CE_REQUIRED_BUILD 19044        ; Windows 10 21H2, per docs/COMPATIBILITY.md
!define CE_REQUIRED_DISK_MB 6144       ; 6 GB free, full build
!define CE_RECOMMENDED_RAM_MB 8192     ; 8 GB minimum, per docs/COMPATIBILITY.md
!define CE_TOTAL_STAGES 5

; PF_AVX2_INSTRUCTIONS_AVAILABLE - MediaPipe and onnxruntime require AVX2.
!define CE_PF_AVX2 40

Var CE_Stage
Var CE_Warnings

; Mirror every stage line into %TEMP%\cutting-edge-setup.log.
; A silent install prints nowhere, so without this a failure leaves no trace at
; all - which is exactly how the first CI failure cost an hour to diagnose.
!macro CE_Log LINE
  Push $9
  ClearErrors
  FileOpen $9 "$TEMP\cutting-edge-setup.log" a
  ${IfNot} ${Errors}
    FileSeek $9 0 END
    FileWrite $9 "${LINE}$\r$\n"
    FileClose $9
  ${EndIf}
  Pop $9
!macroend

!macro CE_Stage TEXT
  IntOp $CE_Stage $CE_Stage + 1
  SetDetailsPrint both
  DetailPrint "[$CE_Stage/${CE_TOTAL_STAGES}] ${TEXT}"
  !insertmacro CE_Log "[$CE_Stage/${CE_TOTAL_STAGES}] ${TEXT}"
  SetDetailsPrint listonly
!macroend

!macro CE_Ok TEXT
  DetailPrint "        OK    ${TEXT}"
  !insertmacro CE_Log "        OK    ${TEXT}"
!macroend

!macro CE_Warn TEXT
  IntOp $CE_Warnings $CE_Warnings + 1
  DetailPrint "        WARN  ${TEXT}"
  !insertmacro CE_Log "        WARN  ${TEXT}"
!macroend

!macro CE_Fail TEXT
  SetDetailsPrint both
  DetailPrint "        FAIL  ${TEXT}"
  !insertmacro CE_Log "        FAIL  ${TEXT}"
  SetDetailsPrint listonly
!macroend

; Stop the install with a reason.
;
; A plain MessageBox still renders under /S, where nobody can dismiss it, so an
; unattended install would hang forever instead of failing. Silent runs therefore
; get the log line and a non-zero error level; only interactive runs get a dialog.
!macro CE_Abort TEXT
  !insertmacro CE_Fail "${TEXT}"
  ${IfNot} ${Silent}
    MessageBox MB_ICONSTOP|MB_OK "${TEXT}"
  ${EndIf}
  SetErrorLevel 2
  Abort "${TEXT}"
!macroend

; ---------------------------------------------------------------------------
; Reports whether the Visual C++ 2015-2022 x64 runtime is registered.
; Both registry views are probed so the result does not depend on whether the
; installer itself is running as 32-bit or 64-bit.
; Pushes "1" (present) or "0" (absent).
; ---------------------------------------------------------------------------
Function CEDetectVCRuntime
  Push $0
  Push $1

  ReadRegDWORD $1 HKLM "SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" "Installed"
  ${If} $1 != 1
    ReadRegDWORD $1 HKLM "SOFTWARE\WOW6432Node\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" "Installed"
  ${EndIf}

  ${If} $1 == 1
    StrCpy $0 "1"
  ${Else}
    StrCpy $0 "0"
  ${EndIf}

  ; Restore $1, then swap the result into the stack while restoring $0.
  Pop $1
  Exch $0
FunctionEnd

; ---------------------------------------------------------------------------
; Stage 1 - system requirements. Blocks only on things that genuinely cannot
; run the product; everything else is reported as a warning.
; ---------------------------------------------------------------------------
Function CEPreflightSystem
  !insertmacro CE_Stage "Checking system requirements"

  ; -- architecture ---------------------------------------------------------
  ${IfNot} ${RunningX64}
    !insertmacro CE_Abort "Cutting Edge v2 requires 64-bit Windows.$\r$\nWindows on ARM and 32-bit Windows are not supported."
  ${EndIf}
  !insertmacro CE_Ok "Architecture: x64"

  ; -- Windows version ------------------------------------------------------
  ${If} ${AtLeastWin10}
    ClearErrors
    ReadRegStr $0 HKLM "SOFTWARE\Microsoft\Windows NT\CurrentVersion" "CurrentBuildNumber"
    ${If} ${Errors}
      !insertmacro CE_Warn "Windows build number could not be read; continuing."
    ${Else}
      IntOp $1 $0 + 0
      ${If} $1 < ${CE_REQUIRED_BUILD}
        !insertmacro CE_Warn "Windows build $0 is older than ${CE_REQUIRED_BUILD} (21H2); WebView2 may need a manual install."
      ${Else}
        !insertmacro CE_Ok "Windows build $0"
      ${EndIf}
    ${EndIf}
  ${Else}
    !insertmacro CE_Abort "Cutting Edge v2 requires Windows 10 (21H2) or Windows 11."
  ${EndIf}

  ; -- AVX2 -----------------------------------------------------------------
  System::Call "kernel32::IsProcessorFeaturePresent(i ${CE_PF_AVX2}) i .r0"
  ${If} $0 == 0
    !insertmacro CE_Abort "Cutting Edge v2 requires a CPU with AVX2.$\r$\nThe pose and embedding models cannot run without it."
  ${EndIf}
  !insertmacro CE_Ok "CPU supports AVX2"

  ; -- physical memory (advisory) ------------------------------------------
  System::Alloc 64
  Pop $1
  ${If} $1 <> 0
    System::Call "*$1(i 64)"
    System::Call "kernel32::GlobalMemoryStatusEx(i r1) i .r2"
    ${If} $2 <> 0
      System::Call "*$1(i, i, l .r3)"
      System::Int64Op $3 / 1048576
      Pop $4
      ${If} $4 > 0
        ${If} $4 < ${CE_RECOMMENDED_RAM_MB}
          !insertmacro CE_Warn "Installed RAM is $4 MB; 8192 MB is the supported minimum."
        ${Else}
          !insertmacro CE_Ok "Installed RAM: $4 MB"
        ${EndIf}
      ${EndIf}
    ${EndIf}
    System::Free $1
  ${EndIf}

  ; -- free disk space ------------------------------------------------------
  ${GetRoot} "$INSTDIR" $0
  ${DriveSpace} "$0\" "/D=F /S=M" $1
  ${If} $1 > 0
    ${If} $1 < ${CE_REQUIRED_DISK_MB}
      !insertmacro CE_Abort "Not enough free space on $0.$\r$\nRequired: ${CE_REQUIRED_DISK_MB} MB$\r$\nAvailable: $1 MB"
    ${EndIf}
    !insertmacro CE_Ok "Free space on $0: $1 MB"
  ${Else}
    !insertmacro CE_Warn "Free space on $0 could not be determined; continuing."
  ${EndIf}
FunctionEnd

; ---------------------------------------------------------------------------
; Stage 2 - install the Visual C++ runtime the frozen Python sidecar links
; against, but only if it is missing and only from the embedded copy.
; ---------------------------------------------------------------------------
Function CEPrerequisiteVCRuntime
  !insertmacro CE_Stage "Checking Visual C++ 2015-2022 x64 runtime"

  Call CEDetectVCRuntime
  Pop $0
  ${If} $0 == "1"
    !insertmacro CE_Ok "Already installed; nothing to do."
    Return
  ${EndIf}

  DetailPrint "        ..    Not present. Installing the bundled runtime."

; The redistributable is embedded only when the build machine staged it.
; $%CE_PREREQ_DIR% is exported by scripts/build-installer.ps1; when it is unset
; this path cannot exist, so the light build compiles without the payload.
!if /FileExists "$%CE_PREREQ_DIR%\vc_redist.x64.exe"
  InitPluginsDir
  SetOutPath "$PLUGINSDIR"
  File "$%CE_PREREQ_DIR%\vc_redist.x64.exe"
  DetailPrint "        ..    Running vc_redist.x64.exe /quiet /norestart"
  ExecWait '"$PLUGINSDIR\vc_redist.x64.exe" /quiet /norestart' $1
  Delete "$PLUGINSDIR\vc_redist.x64.exe"
  SetOutPath "$INSTDIR"

  ; 0 = installed, 1638 = a newer version is already present, 3010 = reboot queued.
  ${If} $1 == 0
    !insertmacro CE_Ok "Runtime installer finished (exit 0)."
  ${ElseIf} $1 == 1638
    !insertmacro CE_Ok "A newer runtime is already present (exit 1638)."
  ${ElseIf} $1 == 3010
    !insertmacro CE_Warn "Runtime installed but Windows requests a restart (exit 3010)."
    SetRebootFlag true
  ${Else}
    !insertmacro CE_Abort "The Visual C++ runtime could not be installed (exit code $1).$\r$\nInstall it manually and run this setup again."
  ${EndIf}
!else
  !warning "vc_redist.x64.exe was not staged; the installer will only report its absence."
  !insertmacro CE_Warn "No runtime was bundled with this build. Install the Microsoft Visual C++ 2015-2022 x64 redistributable if the app fails to start."
!endif
FunctionEnd

; ---------------------------------------------------------------------------
; Stage 3 - prove the prerequisite actually took effect. A prerequisite that
; reports success but does not register is the classic silent installer bug.
; ---------------------------------------------------------------------------
Function CEVerifyPrerequisites
  !insertmacro CE_Stage "Verifying prerequisites"

  Call CEDetectVCRuntime
  Pop $0
  ${If} $0 == "1"
    ReadRegStr $1 HKLM "SOFTWARE\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" "Version"
    ${If} $1 == ""
      ReadRegStr $1 HKLM "SOFTWARE\WOW6432Node\Microsoft\VisualStudio\14.0\VC\Runtimes\x64" "Version"
    ${EndIf}
    !insertmacro CE_Ok "Visual C++ x64 runtime present $1"
  ${Else}
  !if /FileExists "$%CE_PREREQ_DIR%\vc_redist.x64.exe"
    !insertmacro CE_Abort "The Visual C++ runtime did not register after installation.$\r$\nSetup cannot continue safely."
  !else
    !insertmacro CE_Warn "Visual C++ x64 runtime is still absent (nothing was bundled to install)."
  !endif
  ${EndIf}

  ; WebView2 is reported only. Tauri's own webviewInstallMode owns installing it;
  ; duplicating that here would fight the generated installer.
  ReadRegStr $2 HKLM \
    "SOFTWARE\WOW6432Node\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}" "pv"
  ${If} $2 == ""
    ReadRegStr $2 HKLM \
      "SOFTWARE\Microsoft\EdgeUpdate\Clients\{F3017226-FE2A-4295-8BDF-00C3A9A7E4C5}" "pv"
  ${EndIf}
  ${If} $2 == ""
    !insertmacro CE_Ok "WebView2: using the runtime supplied by this installer."
  ${Else}
    !insertmacro CE_Ok "WebView2 runtime detected: $2"
  ${EndIf}
FunctionEnd

; ---------------------------------------------------------------------------
; Stage 5 - confirm what actually landed on disk.
; ---------------------------------------------------------------------------
Function CEVerifyInstallation
  !insertmacro CE_Stage "Verifying the installed application"

  ${IfNot} ${FileExists} "$INSTDIR\${MAINBINARYNAME}.exe"
    !insertmacro CE_Abort "Installation incomplete: ${MAINBINARYNAME}.exe was not written."
  ${EndIf}
  !insertmacro CE_Ok "${MAINBINARYNAME}.exe"

  ; Tauri strips the target triple from externalBin, but do not bet an install on
  ; that: fall back to a wildcard before declaring the sidecar missing.
  ${If} ${FileExists} "$INSTDIR\cutting-edge-backend.exe"
    !insertmacro CE_Ok "cutting-edge-backend.exe (processing sidecar)"
  ${Else}
    ClearErrors
    FindFirst $0 $1 "$INSTDIR\cutting-edge-backend*.exe"
    ${If} ${Errors}
    ${OrIf} $1 == ""
      FindClose $0
      !insertmacro CE_Abort "Installation incomplete: the processing sidecar was not written."
    ${Else}
      !insertmacro CE_Ok "$1 (processing sidecar)"
      FindClose $0
    ${EndIf}
  ${EndIf}

  ${If} ${FileExists} "$INSTDIR\frontend\index.html"
    !insertmacro CE_Ok "frontend\index.html (user interface)"
  ${Else}
    !insertmacro CE_Warn "frontend\index.html was not found where it was expected."
  ${EndIf}

  ${If} ${FileExists} "$INSTDIR\_internal"
    !insertmacro CE_Ok "_internal (frozen Python runtime)"
  ${Else}
    !insertmacro CE_Warn "_internal was not found; the sidecar may be packaged differently in this build."
  ${EndIf}

  ; A support-friendly record of what this machine actually got.
  ClearErrors
  FileOpen $0 "$INSTDIR\install-report.txt" w
  ${IfNot} ${Errors}
    FileWrite $0 "product=${PRODUCTNAME}$\r$\n"
    FileWrite $0 "version=${VERSION}$\r$\n"
    FileWrite $0 "install_dir=$INSTDIR$\r$\n"
    FileWrite $0 "preflight_warnings=$CE_Warnings$\r$\n"
    FileClose $0
    !insertmacro CE_Ok "Wrote install-report.txt"
  ${EndIf}
FunctionEnd

; ===========================================================================
; Tauri hooks
; ===========================================================================

!macro NSIS_HOOK_PREINSTALL
  ; Tauri's Section Install uses $0-$4 after this hook returns, so leave them as found.
  Push $0
  Push $1
  Push $2
  Push $3
  Push $4

  StrCpy $CE_Stage 0
  StrCpy $CE_Warnings 0
  ; Start a fresh stage log; a stale one from an earlier attempt misleads.
  Delete "$TEMP\cutting-edge-setup.log"

  SetDetailsPrint both
  DetailPrint "=============================================="
  DetailPrint " ${PRODUCTNAME} ${VERSION} - staged installation"
  DetailPrint "=============================================="
  SetDetailsPrint listonly

  Call CEPreflightSystem
  Call CEPrerequisiteVCRuntime
  Call CEVerifyPrerequisites

  !insertmacro CE_Stage "Installing application files"
  SetDetailsPrint both

  Pop $4
  Pop $3
  Pop $2
  Pop $1
  Pop $0
!macroend

!macro NSIS_HOOK_POSTINSTALL
  Push $0
  Push $1

  SetDetailsPrint listonly
  Call CEVerifyInstallation

  SetDetailsPrint both
  DetailPrint "=============================================="
  ${If} $CE_Warnings == 0
    DetailPrint " Finished: all ${CE_TOTAL_STAGES} stages completed cleanly."
  ${Else}
    DetailPrint " Finished with $CE_Warnings warning(s) - see the log above."
  ${EndIf}
  DetailPrint "=============================================="

  Pop $1
  Pop $0
!macroend

!macro NSIS_HOOK_PREUNINSTALL
  SetDetailsPrint both
  DetailPrint "Removing ${PRODUCTNAME}..."
  SetDetailsPrint listonly
  ; Written by this hook, so this hook removes it. Projects and user data in
  ; %LOCALAPPDATA% are deliberately left alone.
  Delete "$INSTDIR\install-report.txt"
!macroend

!macro NSIS_HOOK_POSTUNINSTALL
  SetDetailsPrint both
  DetailPrint "${PRODUCTNAME} was removed. Your projects were not deleted."
  SetDetailsPrint listonly
!macroend
