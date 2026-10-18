"""Build an allowlisted source ZIP, manifest, and SHA-256 checksum."""
import hashlib
import json
from pathlib import Path
import tomllib
import zipfile

ROOT_FILES = (".gitignore", ".gitattributes", ".streamlit/config.toml", "app.py",
              "pyproject.toml", "requirements-tested.txt", "README.md", "LICENSE",
              "THIRD_PARTY.md", "VALIDATION.md", "CHANGELOG.md", "install.ps1", "setup.bat",
              "install-gpu.ps1", "start.bat", "start.ps1")
SOURCE_DIRS = ("autosub", "tests", "tools", "docs")
EXTENSIONS = {".py", ".js", ".html", ".ps1", ".bat", ".md"}


def source_files(root: Path) -> list[Path]:
    root = root.resolve()
    result = [root / name for name in ROOT_FILES]
    for folder in SOURCE_DIRS:
        result.extend(p for p in (root / folder).rglob("*")
                      if p.is_file() and p.suffix in EXTENSIONS and "__pycache__" not in p.parts)
    for path in result:
        if not path.is_file() or path.is_symlink() or not path.resolve().is_relative_to(root):
            raise ValueError(f"Unsafe or missing source file: {path.name}")
    return sorted(set(result), key=lambda p: p.relative_to(root).as_posix())


def package(root: Path) -> Path:
    root = root.resolve()
    version = tomllib.loads((root / "pyproject.toml").read_text(encoding="utf-8"))["project"]["version"]
    prefix = f"auto-sub-local-{version}"
    dist = root / "dist"
    dist.mkdir(exist_ok=True)
    files = source_files(root)
    entries = [{"path":p.relative_to(root).as_posix(), "bytes":p.stat().st_size,
                "sha256":hashlib.sha256(p.read_bytes()).hexdigest()} for p in files]
    manifest = {"version":version, "format":"source", "files":entries}
    archive = dist / f"{prefix}-source.zip"
    with zipfile.ZipFile(archive, "w", compression=zipfile.ZIP_DEFLATED) as output:
        for path in files:
            output.write(path, f"{prefix}/{path.relative_to(root).as_posix()}")
        output.writestr(f"{prefix}/PACKAGE-MANIFEST.json", json.dumps(manifest, ensure_ascii=False, indent=2))
    digest = hashlib.sha256(archive.read_bytes()).hexdigest()
    (dist / "SHA256SUMS.txt").write_text(f"{digest}  {archive.name}\n", encoding="ascii")
    (dist / "source-manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    print(json.dumps({"archive":str(archive), "files":len(files), "bytes":archive.stat().st_size,
                      "sha256":digest}))
    return archive


if __name__ == "__main__":
    package(Path(__file__).resolve().parents[1])
