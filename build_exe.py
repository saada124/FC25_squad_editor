import os
import subprocess
import sys

def build():
    print("Building standalone executable FC25_Squad_Editor.exe...")
    base_dir = os.path.dirname(os.path.abspath(__file__))
    src_dir = os.path.join(base_dir, "src")
    main_script = os.path.join(base_dir, "main.py")
    
    pyinstaller_exe = os.path.join(base_dir, "venv", "Scripts", "pyinstaller.exe")
    if not os.path.exists(pyinstaller_exe):
        pyinstaller_exe = "pyinstaller"

    presets_src = os.path.join(base_dir, "player_presets")
    assets_src = os.path.join(base_dir, "assets")
    cmd = [
        pyinstaller_exe,
        "--name=FC25_Squad_Editor",
        "--onefile",
        "--windowed",
        f"--paths={src_dir}",
        f"--add-data={presets_src};player_presets",
        f"--add-data={assets_src};assets",
        "--hidden-import=PIL",
        "--hidden-import=PIL.Image",
        "--hidden-import=PIL.ImageDraw",
        "--hidden-import=PIL.ImageFont",
        "--clean",
        main_script
    ]
    
    print("Running:", " ".join(cmd))
    result = subprocess.run(cmd, cwd=base_dir)
    if result.returncode == 0:
        dist_exe = os.path.join(base_dir, "dist", "FC25_Squad_Editor.exe")
        print("\n" + "="*60)
        print("BUILD SUCCESSFUL!")
        print("Standalone Executable generated at:")
        print(dist_exe)
        print("="*60)
    else:
        print("Build failed with returncode:", result.returncode)
        sys.exit(result.returncode)

if __name__ == "__main__":
    build()
