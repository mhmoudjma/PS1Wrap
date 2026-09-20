# PS1Wrap

Convert **PowerShell (.ps1) scripts into standalone Windows EXE files** — directly from **Linux**, no PowerShell SDK or Windows tools required.

## 🧠 How it works

This tool doesn't try to "interpret" or "translate" PowerShell code itself. Instead, it uses a **wrapper approach**:

1. Your `.ps1` script is embedded as an **Embedded Resource** inside a small C# project.
2. The project is built with `dotnet publish` using `-r win-x64` and `PublishSingleFile=true`, producing a single self-contained `.exe` that runs on Windows (no .NET installation required on the target machine).
3. When the EXE is run on Windows:
   - It extracts the original script to a temporary file (`%TEMP%`).
   - It launches `powershell.exe -ExecutionPolicy Bypass -File script.ps1`, forwarding any arguments.
   - After execution finishes, it deletes the temp file and returns the same exit code as the script.

The result is a **real EXE** (not an obfuscated script) that runs on any Windows machine with PowerShell installed — which is every modern Windows system by default.

## ✅ Requirements

- **Linux** (or any OS with .NET SDK support)
- [.NET SDK 6.0](https://dotnet.microsoft.com/download) or later (provides cross-compilation to `win-x64`)

Verify it's installed:
```bash
dotnet --version
```

## 📦 Installation

```bash
git clone https://github.com/mhmoudjma/PS1Wrap
cd PS1Wrap
```

No external Python dependencies — the script only uses the standard library.

## 🚀 Usage

### Convert an existing `.ps1` file
```bash
python3 ps1_to_exe_linux.py -f script.ps1 -o output.exe
```

### Convert inline PowerShell code
```bash
python3 ps1_to_exe_linux.py -c "Write-Host 'Hello World'" -o hello.exe
```

### Options

| Option | Description |
|---|---|
| `-f, --file` | Path to a `.ps1` file to convert |
| `-c, --code` | Inline PowerShell code instead of a file |
| `-o, --output` | **(required)** Path for the output EXE |
| `-i, --icon` | Path to a custom `.ico` icon for the EXE |
| `--no-console` | Hide the console window at runtime (WinExe mode) |
| `--require-admin` | Add a manifest requesting admin privileges (UAC prompt) |

### Advanced example
```bash
python3 ps1_to_exe_linux.py \
  -f backup_script.ps1 \
  -o BackupTool.exe \
  -i icon.ico \
  --no-console \
  --require-admin
```

## ⚙️ Build process under the hood

The tool automatically generates:
- `Program.cs` — the C# code that extracts and runs the script
- `*.csproj` — a .NET project file configured per your options (icon, manifest, output type)
- `app.manifest` — only when `--require-admin` is used

All of this is generated in a temporary directory (`tempfile.TemporaryDirectory`) and cleaned up automatically after the build — nothing is left on your machine.

## ⚠️ Notes

- The generated EXE **requires PowerShell to be present on the target Windows machine** (installed by default).
- The output is typically 60–70 MB since it's **self-contained** (bundles the .NET runtime).
- This tool does not inspect or modify the content of your PowerShell script — you're responsible for the content of anything you convert.
- Tested with .NET 6/7/8 SDK.

## 📄 License

[MIT](LICENSE)


