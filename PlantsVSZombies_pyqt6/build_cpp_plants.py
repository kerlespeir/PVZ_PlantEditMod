from __future__ import annotations

import shutil
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
CPP_DIR = BASE_DIR / "cpp_plants"
BUILD_DIR = CPP_DIR / "build"


def main() -> int:
    if shutil.which("cmake"):
        BUILD_DIR.mkdir(exist_ok=True)
        subprocess.run(["cmake", "-S", str(CPP_DIR), "-B", str(BUILD_DIR)], check=True)
        subprocess.run(["cmake", "--build", str(BUILD_DIR)], check=True)
        return 0

    compiler = shutil.which("c++") or shutil.which("clang++") or shutil.which("g++")
    if not compiler:
        print("No C++ compiler found. Install cmake or clang++/g++.", file=sys.stderr)
        return 1

    out_dir = BASE_DIR / "plugins" / "plants"
    out_dir.mkdir(parents=True, exist_ok=True)
    suffix = ".dylib" if sys.platform == "darwin" else ".so"
    for source in CPP_DIR.glob("*.cpp"):
        out = out_dir / f"{source.stem}{suffix}"
        subprocess.run(
            [
                compiler,
                "-std=c++17",
                "-shared",
                "-fPIC",
                "-I",
                str(BASE_DIR / "cpp_api"),
                str(source),
                "-o",
                str(out),
            ],
            check=True,
        )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
