"""
build_exe.py
-------------
Convenience script to produce a single-folder Windows executable with
PyInstaller. Run this ON WINDOWS (PyInstaller does not cross-compile):

    pip install -r requirements.txt
    pip install pyinstaller
    python build_exe.py

This drives PyInstaller with TransferManagementSystem.spec, the same
spec the GitHub Actions workflow uses, so a local build and a CI build
produce the same result: dist/TransferManagementSystem/TransferManagementSystem.exe

Point Settings -> Database Location at a shared network folder afterwards
for multi-user use; see README.md for details.
"""
import subprocess
import sys


def main():
    args = [sys.executable, "-m", "PyInstaller", "--noconfirm", "TransferManagementSystem.spec"]
    subprocess.run(args, check=True)


if __name__ == "__main__":
    main()
