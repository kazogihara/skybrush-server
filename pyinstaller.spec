# -*- mode: python -*-

from importlib import import_module
from pathlib import Path

from PyInstaller import __version__ as pyinstaller_version
from PyInstaller.archive.pyz_crypto import PyiBlockCipher

import os
import sys

key = os.environ.get("PYINSTALLER_KEY")
single_file = True
name = "skybrushd"

###########################################################################

# Make sure we have an encryption key if we are using PyInstaller 4.x or later.
# Encryption is broken in PyInstaller 3.6
if pyinstaller_version >= "4.0":
    if not key:
        import secrets
        key = secrets.token_urlsafe(24)
else:
    if key:
        raise RuntimeError("encryption not supported with PyInstaller <4.0")

# Create the encryption cipher
cipher = PyiBlockCipher(key) if key else None

# Prevent TkInter to be included in the bundle, step 1
sys.modules["FixTk"] = None

# Extra modules to import
extra_modules = set([
    "flockwave.server.config"
])

# Modules to exclude
exclude_modules = [
    # No Tcl/Tk
    "FixTk", "tcl", "tk", "_tkinter", "tkinter", "Tkinter"
]

# Parse default configuration
root_dir = Path.cwd()
config_file = str(root_dir / "src" / "flockwave" / "server" / "config.py")
config = {}
exec(
    compile(
        open(config_file).read(), "config.py", mode="exec", dont_inherit=True
    ),
    None,
    config
)

# Make sure to include all extensions mentioned in the config
def extension_module(name):
    return "flockwave.server.ext.{0}".format(name)

extra_modules.add(extension_module("ext_manager"))  # this is implicitly loaded
extra_modules.update(
    extension_module(ext_name)
    for ext_name in config["EXTENSIONS"]
    if not ext_name.startswith("_")
)

# Prepare the dependency table
dependencies = {}
if sys.platform.lower().startswith("linux"):
    dependencies["smpte_timecode"] = ["mido.backends.rtmidi"]

# Add the extensions listed in the config, plus any of the extensions that
# they depend on
changed = True
while changed:
    changed = False
    print(repr(extra_modules))
    for module_name in sorted(extra_modules):
        if module_name.startswith("flockwave.server.ext."):
            try:
                imported_module = import_module(module_name)
                if hasattr(imported_module, "get_dependencies"):
                    deps = imported_module.get_dependencies()
                elif hasattr(imported_module, "dependencies"):
                    deps = imported_module.dependencies
                else:
                    deps = ()
            except ImportError:
                deps = ()
            if deps:
                deps = set(extension_module(dep) for dep in deps)
                new_deps = deps - extra_modules
                if new_deps:
                    extra_modules.update(new_deps)
                    changed = True

# Add some extra extension-dependent dependencies
for ext_name in config["EXTENSIONS"]:
    if ext_name in dependencies:
        extra_modules.update(dependencies[ext_name])

# Now comes the PyInstaller dance
a = Analysis(
    [str(root_dir / "src" / "flockwave" / "server" / "__main__.py")],
    pathex=[str(root_dir / "src")],
    binaries=[],
    datas=[],
    hiddenimports=sorted(extra_modules),
    hookspath=[root_dir / "etc" / "deployment"],
    runtime_hooks=[root_dir / "etc" / "deployment" / "runtime_hook.py"],
    excludes=exclude_modules,
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=cipher
)
pyz = PYZ(a.pure, a.zipped_data, cipher=cipher)

if single_file:
    exe = EXE(
        pyz,
        a.scripts,
        a.binaries,
        a.zipfiles,
        a.datas,
        name=name,
        debug=False,
        strip=False,
        upx=True,
        runtime_tmpdir=None,
        console=True
    )
else:
    exe = EXE(
        pyz,
        a.scripts,
        exclude_binaries=True,
        name=name,
        debug=False,
        strip=False,
        upx=True,
        console=True
    )
    coll = COLLECT(
        exe,
        a.binaries,
        a.zipfiles,
        a.datas,
        strip=False,
        upx=True,
        name=name
    )
