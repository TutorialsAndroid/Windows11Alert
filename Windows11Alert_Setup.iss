#define MyAppName "Windows11Alert"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "Windows11Alert"
#define MyAppExeName "Windows11Alert.exe"

[Setup]
AppId={{7D2D0B32-6E8A-4D4C-A749-WINDOWS11ALERT}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
DefaultDirName={autopf}\Windows11Alert
DefaultGroupName={#MyAppName}
OutputDir=Output
OutputBaseFilename=Windows11Alert_Setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
DisableProgramGroupPage=yes
UninstallDisplayIcon={app}\{#MyAppExeName}
SetupIconFile=icons\alert.ico
ArchitecturesInstallIn64BitMode=x64

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Files]
Source: "D:\terminal-chat\TelegramPCAlert\dist\Windows11Alert.exe"; DestDir: "{app}"; Flags: ignoreversion
Source: "D:\terminal-chat\TelegramPCAlert\dist\uninstaller.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Windows11Alert"; Filename: "{app}\Windows11Alert.exe"
Name: "{autodesktop}\Windows11Alert"; Filename: "{app}\Windows11Alert.exe"; Tasks: desktopicon

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: unchecked

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "Windows11Alert"; ValueData: """{app}\Windows11Alert.exe"""; Flags: uninsdeletevalue

[Run]
Filename: "{app}\Windows11Alert.exe"; Description: "Start Windows11Alert now"; Flags: nowait postinstall skipifsilent

[UninstallRun]
Filename: "taskkill"; Parameters: "/F /IM Windows11Alert.exe"; Flags: runhidden
Filename: "taskkill"; Parameters: "/F /IM uninstaller.exe"; Flags: runhidden

[UninstallDelete]
Type: files; Name: "{app}\.env"
Type: files; Name: "C:\ProgramData\Windows11Alert_log.txt"
Type: files; Name: "C:\ProgramData\Windows11Alert_last_event.txt"
Type: dirifempty; Name: "{app}"

[Code]
var
  ConfigPage: TInputQueryWizardPage;

procedure InitializeWizard;
begin
  ConfigPage := CreateInputQueryPage(
    wpSelectDir,
    'Telegram Bot Configuration',
    'Enter your Telegram bot details',
    'Please enter your Telegram Bot Token and Chat ID. These values will be saved locally in a .env file.'
  );

  ConfigPage.Add('Telegram Bot Token:', False);
  ConfigPage.Add('Telegram Chat ID:', False);
end;

function NextButtonClick(CurPageID: Integer): Boolean;
begin
  Result := True;

  if CurPageID = ConfigPage.ID then
  begin
    if Trim(ConfigPage.Values[0]) = '' then
    begin
      MsgBox('Please enter Telegram Bot Token.', mbError, MB_OK);
      Result := False;
      Exit;
    end;

    if Trim(ConfigPage.Values[1]) = '' then
    begin
      MsgBox('Please enter Telegram Chat ID.', mbError, MB_OK);
      Result := False;
      Exit;
    end;
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
var
  EnvFilePath: String;
  EnvContent: String;
begin
  if CurStep = ssPostInstall then
  begin
    EnvFilePath := ExpandConstant('{app}\.env');

    EnvContent :=
      'TELEGRAM_BOT_TOKEN=' + ConfigPage.Values[0] + #13#10 +
      'TELEGRAM_CHAT_ID=' + ConfigPage.Values[1] + #13#10;

    SaveStringToFile(EnvFilePath, EnvContent, False);
  end;
end;