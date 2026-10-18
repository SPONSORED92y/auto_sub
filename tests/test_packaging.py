import importlib.util
from pathlib import Path


def test_source_manifest_contains_frontend_and_install_guide_but_no_local_data():
    root = Path(__file__).resolve().parents[1]
    spec = importlib.util.spec_from_file_location("package_source", root / "tools/package_source.py")
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    files = [p.relative_to(root).as_posix() for p in module.source_files(root)]
    assert "autosub/editor_frontend/editor.js" in files
    assert "autosub/editor_frontend/index.html" in files
    assert "docs/INSTALL_WINDOWS.md" in files
    assert "install.ps1" in files and "setup.bat" in files
    assert ".streamlit/config.toml" in files
    assert all(not name.startswith(("models/", "outputs/", ".venv/", ".tools/", ".python/", "dist/")) for name in files)
    assert all("__pycache__" not in name and not name.endswith((".wav", ".mp3", ".m4a", ".autosub.json")) for name in files)
