# PyInstaller spec: standalone Sotto.app (arm64).
# Сборка: scripts/build_app.sh (или pyinstaller --noconfirm packaging/sotto.spec)
import re
from pathlib import Path

from PyInstaller.utils.hooks import collect_all

ROOT = Path(SPECPATH).parent
VERSION = re.search(
    r'__version__ = "([^"]+)"', (ROOT / "sotto" / "__init__.py").read_text()
).group(1)

datas, binaries, hiddenimports = [], [], []
for pkg in ("mlx", "mlx_whisper"):  # metallib/dylib mlx + assets whisper (mel, tiktoken)
    d, b, h = collect_all(pkg)
    datas += d
    binaries += b
    hiddenimports += h
hiddenimports += ["tiktoken_ext", "tiktoken_ext.openai_public"]

a = Analysis(
    [str(ROOT / "packaging" / "sotto_entry.py")],
    pathex=[str(ROOT)],
    datas=datas,
    binaries=binaries,
    hiddenimports=hiddenimports,
    # torch нужен mlx_whisper только для конвертации PyTorch-чекпойнтов — в
    # рантайме Sotto не импортируется, а это -437 МБ
    excludes=["torch", "torchaudio", "tkinter", "matplotlib", "PIL", "IPython", "pandas"],
    noarchive=False,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    exclude_binaries=True,
    name="Sotto",
    console=False,
    target_arch="arm64",
)

coll = COLLECT(exe, a.binaries, a.datas, name="Sotto")

app = BUNDLE(
    coll,
    name="Sotto.app",
    icon=str(ROOT / "packaging" / "Sotto.icns"),
    bundle_identifier="com.sotto.app",
    version=VERSION,
    info_plist={
        "CFBundleName": "Sotto",
        "CFBundleShortVersionString": VERSION,
        "LSUIElement": True,  # только menu bar, без иконки в Dock
        "NSHighResolutionCapable": True,
        "NSMicrophoneUsageDescription": (
            "Sotto записывает голос, пока зажата клавиша диктовки, "
            "и распознаёт его локально на этом Mac."
        ),
        "LSMinimumSystemVersion": "14.0",
    },
)
