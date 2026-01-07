"""Setup script with custom post-install hook to build Swift binaries."""

import subprocess
import sys
from pathlib import Path

from setuptools import setup
from setuptools.command.develop import develop
from setuptools.command.install import install


def build_swift_binaries():
    """Compile Swift source files to binaries."""
    project_root = Path(__file__).parent
    swift_src = project_root / "src" / "apple_foundation" / "swift"
    bin_dir = project_root / "bin"
    
    bin_dir.mkdir(exist_ok=True)
    
    swift_files = [
        ("generate.swift", "generate"),
        ("transcribe.swift", "transcribe"),
    ]
    
    for src_file, output_name in swift_files:
        src_path = swift_src / src_file
        output_path = bin_dir / output_name
        
        if src_path.exists():
            print(f"Compiling {src_file}...")
            try:
                subprocess.run(
                    ["swiftc", str(src_path), "-o", str(output_path)],
                    check=True,
                    capture_output=True,
                    text=True,
                )
            except subprocess.CalledProcessError as e:
                print(f"Warning: Failed to compile {src_file}: {e.stderr}", file=sys.stderr)
            except FileNotFoundError:
                print("Warning: Swift compiler not found. Install Xcode command line tools.", file=sys.stderr)
                break


class PostInstallCommand(install):
    """Post-installation: build Swift binaries."""
    
    def run(self):
        install.run(self)
        build_swift_binaries()


class PostDevelopCommand(develop):
    """Post-develop installation: build Swift binaries."""
    
    def run(self):
        develop.run(self)
        build_swift_binaries()


setup(
    cmdclass={
        "install": PostInstallCommand,
        "develop": PostDevelopCommand,
    },
)
