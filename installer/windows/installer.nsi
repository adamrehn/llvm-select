; Include the Modern UI 2 Header File
!include "MUI2.nsh"

; The name of the installer
Name "LLVM-Select"

; The filename of the installer
OutFile "llvm-select-windows.exe"

; The default installation directory
InstallDir C:\llvm

; Request application privileges for Windows Vista and above
RequestExecutionLevel admin

; Default Settings
ShowInstDetails show
ShowUninstDetails show

;--------------------------------

; Installer Pages
!insertmacro MUI_PAGE_DIRECTORY
!insertmacro MUI_PAGE_INSTFILES

; Uninstaller Pages
!insertmacro MUI_UNPAGE_CONFIRM
!insertmacro MUI_UNPAGE_INSTFILES
!insertmacro MUI_UNPAGE_FINISH

; Languages
!insertmacro MUI_LANGUAGE "English"

; Version Settings
VIAddVersionKey /LANG=${LANG_ENGLISH} "ProductName" "LLVM-Select Installer"
VIAddVersionKey /LANG=${LANG_ENGLISH} "Comments" "LLVM-Select Installer"
VIAddVersionKey /LANG=${LANG_ENGLISH} "CompanyName" "Adam Rehn"
VIAddVersionKey /LANG=${LANG_ENGLISH} "LegalCopyright" "Copyright (c) 2016, Adam Rehn"
VIAddVersionKey /LANG=${LANG_ENGLISH} "FileDescription" "LLVM-Select Installer"
VIAddVersionKey /LANG=${LANG_ENGLISH} "FileVersion" "__VERSION__.0"
VIProductVersion "__VERSION__.0"

;--------------------------------

; Uninstaller instructions
Section "Uninstall"

    ; No reboot required
    SetRebootFlag false
    
    ; Remove the bin directory from the system PATH
    Exec `powershell -NoProfile -ExecutionPolicy Bypass -Command "[Environment]::SetEnvironmentVariable('Path', [Environment]::GetEnvironmentVariable('Path', 'Machine').Replace(';$INSTDIR\bin', ''), 'Machine');"`
    
    ; Delete the installation directory
    RMDir /r $INSTDIR

SectionEnd

; Installer instructions
Section ""

    ; Set output path to the installation directory.
    SetOutPath $INSTDIR
    
    ; Install the executables
    File /r bin
    CreateDirectory $INSTDIR\versions
	
    ; Write the uninstaller
    WriteUninstaller $INSTDIR\uninstall.exe
    
    ; Add the bin directory to the system PATH
    Exec `powershell -NoProfile -ExecutionPolicy Bypass -Command "[Environment]::SetEnvironmentVariable('Path', [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';$INSTDIR\bin', 'Machine');"`
    
SectionEnd
