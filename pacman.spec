# pacman.spec -- build with:  make package
from PyInstaller.utils.hooks import collect_submodules

a = Analysis(
    ["pac-man.py"],
    pathex=["."],
    datas=[
        ("assets", "assets"),          # sprites, fonts and their licences
        ("config.json", "."),          # default configuration
        ("README.md", "."),            # instructions
    ],
    # load_optional() imports scenes by name at run time
    hiddenimports=collect_submodules("pacman") + collect_submodules("mazegenerator"),
)
pyz = PYZ(a.pure)
exe = EXE(
    pyz, a.scripts, a.binaries, a.datas, [],
    name="pac-man",
    console=True,          # keep stderr warnings visible; False hides the terminal
    upx=False,
)