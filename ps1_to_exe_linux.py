#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
ps1_to_exe_linux.py (v2 - بدون PowerShell SDK)
تحويل كود PowerShell إلى EXE على Linux بطريقة موثوقة.

الطريقة: دمج السكربت داخل EXE، وعند التشغيل يُستخرج إلى ملف مؤقت
ويُستدعى powershell.exe كـ subprocess.
"""

import argparse
import os
import shutil
import subprocess
import sys
import tempfile
import re


# ============================================================
# كود C# بسيط: يستخرج السكربت ويستدعي powershell.exe
# ============================================================
CSHARP_PROGRAM = r'''using System;
using System.IO;
using System.Reflection;
using System.Diagnostics;

class Program
{
    static int Main(string[] args)
    {
        try
        {
            // 1) استخراج السكربت المدموج إلى ملف مؤقت
            string script;
            var assembly = Assembly.GetExecutingAssembly();
            using (Stream stream = assembly.GetManifestResourceStream("script.ps1"))
            {
                if (stream == null)
                {
                    Console.Error.WriteLine("[!] Embedded resource 'script.ps1' not found.");
                    return 1;
                }
                using (StreamReader reader = new StreamReader(stream))
                {
                    script = reader.ReadToEnd();
                }
            }

            // 2) كتابة السكربت في ملف مؤقت بترميز UTF-8 مع BOM
            string tempScript = Path.Combine(
                Path.GetTempPath(),
                "ps1exe_" + Guid.NewGuid().ToString("N") + ".ps1"
            );
            File.WriteAllText(tempScript, script, new System.Text.UTF8Encoding(true));

            // 3) تجهيز الوسائط
            string quotedArgs = "";
            foreach (var a in args)
            {
                quotedArgs += " \"" + a.Replace("\"", "\\\"") + "\"";
            }

            string psArgs = "-NoProfile -ExecutionPolicy Bypass -File \"" + tempScript + "\"" + quotedArgs;

            // 4) تشغيل powershell.exe
            var psi = new ProcessStartInfo
            {
                FileName = "powershell.exe",
                Arguments = psArgs,
                UseShellExecute = false,
                CreateNoWindow = false
            };

            var proc = Process.Start(psi);
            proc.WaitForExit();

            // 5) تنظيف الملف المؤقت
            try { File.Delete(tempScript); } catch { }

            return proc.ExitCode;
        }
        catch (Exception ex)
        {
            Console.Error.WriteLine("[!] " + ex.ToString());
            return 1;
        }
    }
}
'''


# ============================================================
# قالب .csproj — لا يوجد PowerShell SDK هنا
# ============================================================
CSPROJ_TEMPLATE = '''<Project Sdk="Microsoft.NET.Sdk">
  <PropertyGroup>
    <OutputType>{output_type}</OutputType>
    <TargetFramework>net6.0</TargetFramework>
    <ImplicitUsings>enable</ImplicitUsings>
    <Nullable>disable</Nullable>
    <RuntimeIdentifier>win-x64</RuntimeIdentifier>
    <PublishSingleFile>true</PublishSingleFile>
    <SelfContained>true</SelfContained>
    <AssemblyName>{assembly_name}</AssemblyName>
    <RootNamespace>{assembly_name}</RootNamespace>
    {icon_line}
    {manifest_line}
    <DebugType>none</DebugType>
    <InvariantGlobalization>true</InvariantGlobalization>
    <NoWarn>NETSDK1138</NoWarn>
  </PropertyGroup>
  <ItemGroup>
    <EmbeddedResource Include="script.ps1">
      <LogicalName>script.ps1</LogicalName>
    </EmbeddedResource>
  </ItemGroup>
</Project>
'''


MANIFEST_TEMPLATE = '''<?xml version="1.0" encoding="utf-8"?>
<assembly manifestVersion="1.0" xmlns="urn:schemas-microsoft-com:asm.v1">
  <trustInfo xmlns="urn:schemas-microsoft-com:asm.v2">
    <security>
      <requestedPrivileges xmlns="urn:schemas-microsoft-com:asm.v3">
        <requestedExecutionLevel level="requireAdministrator" uiAccess="false" />
      </requestedPrivileges>
    </security>
  </trustInfo>
</assembly>
'''


# ============================================================
# دوال مساعدة
# ============================================================
def sanitize_assembly_name(name: str) -> str:
    name = os.path.splitext(os.path.basename(name))[0]
    name = re.sub(r'[^a-zA-Z0-9_]', '_', name)
    if not name or name[0].isdigit():
        name = "PS2EXE_" + name
    return name


def check_dotnet():
    if not shutil.which("dotnet"):
        print("[!] لم يتم العثور على dotnet.")
        sys.exit(1)
    try:
        r = subprocess.run(["dotnet", "--version"], capture_output=True, text=True, check=True)
        print(f"[*] .NET SDK: {r.stdout.strip()}")
    except Exception:
        print("[!] dotnet لا يعمل.")
        sys.exit(1)


# ============================================================
# التحويل
# ============================================================
def convert(input_ps1: str, output_exe: str, icon: str = None,
            no_console: bool = False, require_admin: bool = False):

    check_dotnet()

    output_exe = os.path.abspath(output_exe)
    assembly_name = sanitize_assembly_name(output_exe)
    output_dir = os.path.dirname(output_exe) or "."
    os.makedirs(output_dir, exist_ok=True)

    with tempfile.TemporaryDirectory(prefix="ps2exe_") as tmpdir:
        shutil.copyfile(input_ps1, os.path.join(tmpdir, "script.ps1"))

        with open(os.path.join(tmpdir, "Program.cs"), "w", encoding="utf-8") as f:
            f.write(CSHARP_PROGRAM)

        icon_line = ""
        if icon:
            icon_abs = os.path.abspath(icon)
            if not os.path.isfile(icon_abs):
                print(f"[!] الأيقونة غير موجودة: {icon_abs}")
                sys.exit(1)
            shutil.copyfile(icon_abs, os.path.join(tmpdir, "icon.ico"))
            icon_line = "<ApplicationIcon>icon.ico</ApplicationIcon>"

        manifest_line = ""
        if require_admin:
            with open(os.path.join(tmpdir, "app.manifest"), "w", encoding="utf-8") as f:
                f.write(MANIFEST_TEMPLATE)
            manifest_line = "<ApplicationManifest>app.manifest</ApplicationManifest>"

        output_type = "WinExe" if no_console else "Exe"

        csproj_content = CSPROJ_TEMPLATE.format(
            output_type=output_type,
            assembly_name=assembly_name,
            icon_line=icon_line,
            manifest_line=manifest_line
        )
        with open(os.path.join(tmpdir, f"{assembly_name}.csproj"), "w", encoding="utf-8") as f:
            f.write(csproj_content)

        publish_dir = os.path.join(tmpdir, "publish")
        cmd = [
            "dotnet", "publish",
            "-c", "Release",
            "-r", "win-x64",
            "--self-contained", "true",
            "/p:PublishSingleFile=true",
            "-o", publish_dir
        ]

        print("[*] جاري البناء...")
        try:
            subprocess.run(cmd, cwd=tmpdir, check=True)
        except subprocess.CalledProcessError:
            print("[!] فشل البناء.")
            sys.exit(1)

        produced_exe = os.path.join(publish_dir, f"{assembly_name}.exe")
        if not os.path.isfile(produced_exe):
            candidates = [f for f in os.listdir(publish_dir) if f.endswith(".exe")]
            if not candidates:
                print("[!] لا يوجد EXE في المخرجات.")
                sys.exit(1)
            produced_exe = os.path.join(publish_dir, candidates[0])

        if os.path.isdir(output_exe):
            output_exe = os.path.join(output_exe, os.path.basename(produced_exe))

        shutil.copyfile(produced_exe, output_exe)
        size_mb = os.path.getsize(output_exe) / (1024 * 1024)
        print(f"[+] تم إنشاء: {output_exe}  ({size_mb:.1f} MB)")


# ============================================================
# نقطة الدخول
# ============================================================
def main():
    parser = argparse.ArgumentParser(description="PowerShell -> EXE (بدون PowerShell SDK)")
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("-f", "--file", help="مسار ملف .ps1")
    group.add_argument("-c", "--code", help="كود PowerShell كنص")

    parser.add_argument("-o", "--output", required=True, help="مسار EXE الناتج")
    parser.add_argument("-i", "--icon", help="أيقونة .ico")
    parser.add_argument("--no-console", action="store_true", help="إخفاء نافذة الكونسول")
    parser.add_argument("--require-admin", action="store_true", help="طلب صلاحيات المسؤول")

    args = parser.parse_args()

    if args.code:
        with tempfile.NamedTemporaryFile("w", suffix=".ps1",
                                         delete=False, encoding="utf-8") as f:
            f.write(args.code)
            temp_ps1 = f.name
        try:
            convert(temp_ps1, args.output, args.icon,
                    args.no_console, args.require_admin)
        finally:
            os.unlink(temp_ps1)
    else:
        if not os.path.isfile(args.file):
            print(f"[!] ملف الإدخال غير موجود: {args.file}")
            sys.exit(1)
        convert(args.file, args.output, args.icon,
                args.no_console, args.require_admin)


if __name__ == "__main__":
    main()
