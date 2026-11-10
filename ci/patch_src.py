#!/usr/bin/env python3
"""Apply environment-only patches to the freshly cloned upstream tree.

Everything here exists because the upstream research tree hardcodes its author's Mac
(`/Users/kexin/...`), a 13+ GiB host, or `/Applications/Xcode.app`. None of it changes
what the build computes: only where it looks for inputs and which host it agrees to run on.

Each replacement asserts that the original text is present exactly once, so an upstream
change fails loudly instead of silently patching the wrong thing.
"""
from __future__ import annotations

import sys
from pathlib import Path

SRC = Path(sys.argv[1] if len(sys.argv) > 1 else "src").resolve()


def patch(rel: str, old: str, new: str) -> None:
    path = SRC / rel
    text = path.read_text()
    count = text.count(old)
    if count != 1:
        raise SystemExit(f"{rel}: expected exactly 1 occurrence, found {count}:\n{old[:200]}")
    path.write_text(text.replace(old, new))
    print(f"patched {rel}")


# 1. ASM jars: the author's Gradle cache path does not exist off a Mac; use the local cache.
patch(
    "tools/build_method_splitter.py",
    '        "/Users/kexin/.gradle/wrapper/dists/gradle-*-bin/*/gradle-*/lib/asm-%s.jar" % ASM_VERSION,\n'
    '        "/Users/kexin/.gradle/wrapper/dists/gradle-*-bin/*/gradle-*/lib/asm-tree-%s.jar" % ASM_VERSION,',
    '        str(CACHE / ("asm-%s.jar" % ASM_VERSION)),\n'
    '        str(CACHE / ("asm-tree-%s.jar" % ASM_VERSION)),',
)
patch(
    "tools/build_method_splitter.py",
    '    for artifact in ("asm-analysis", "asm-util"):',
    '    for artifact in ("asm", "asm-tree", "asm-analysis", "asm-util"):',
)

# 2. The AAR CLI is a private registry binary. The CI checkout has none; the shim is on PATH.
patch(
    "tools/prepare_shader_toolchain.py",
    "    aar='/Users/kexin/Documents/Codex/monitor/bin/aar';command=[sys.executable,'-B',str(Path(__file__).resolve()),'--cache-only']",
    "    import shutil as _shutil\n"
    "    aar = _shutil.which('aar')\n"
    "    if not aar: raise SystemExit('aar shim missing from PATH')\n"
    "    command=[sys.executable,'-B',str(Path(__file__).resolve()),'--cache-only']",
)

# 3b. cmake's compiler probe writes scratch files under TMPDIR, which the seatbelt profile
#     only opens for `work`; point TMPDIR there instead of denying /private/var/folders.
patch(
    "tools/prepare_shader_toolchain.py",
    "env={'PYTHONDONTWRITEBYTECODE':'1','DEVELOPER_DIR':'/Applications/Xcode.app/Contents/Developer'}",
    "env={'PYTHONDONTWRITEBYTECODE':'1','DEVELOPER_DIR':'/Applications/Xcode.app/Contents/Developer','TMPDIR':str(work/'tmp')}",
)
#    versioned bundles and we symlink the generic name. Seatbelt resolves symlinks, so a
#    rule naming "/Applications/Xcode.app" does not cover "/Applications/Xcode_26.3.app";
#    widen the shader-toolchain sandbox to the bundle directory instead.
patch(
    "tools/prepare_shader_toolchain.py",
    "'/System','/usr','/bin','/Library/Apple/System','/Applications/Xcode.app',CACHE,work",
    "'/System','/usr','/bin','/Library/Apple/System','/Applications',CACHE,work",
)

# 3c. Same TMPDIR issue for the OpenAL build, which reuses the shader sandbox profile.
patch(
    "tools/build_openal_soft.py",
    "env={'SDKROOT':sdk,'DEVELOPER_DIR':'/Applications/Xcode.app/Contents/Developer','PYTHONDONTWRITEBYTECODE':'1'}",
    "env={'SDKROOT':sdk,'DEVELOPER_DIR':'/Applications/Xcode.app/Contents/Developer','PYTHONDONTWRITEBYTECODE':'1','TMPDIR':str(work/'tmp')}",
)

# 4. A0 reference evidence: the committed copy is a Mac-launcher inventory with the
#    author's absolute paths. Point the tool at the reference this workflow rebuilds.
patch(
    "tools/prepare_b0.py",
    '    baseline = ROOT / "artifacts/evidence/a0-desktop-reference"',
    '    baseline = Path(__import__("os").environ.get("MCFAO_A0")\n'
    '                     or ROOT / "artifacts/evidence/a0-desktop-reference")',
)

# 5. Host memory gate: this pipeline's own guard demands heap <= 45% of physical RAM,
#    which forces >=13.3 GiB for the 6 GiB client analysis. GitHub's runner has 7 GiB.
#    The measured peak RSS of this step is 4.0 GiB, so we lower the guard to the runner's
#    real budget and allow 4/5 GiB so a smaller heap can be tried if 6 still gets killed.
patch(
    "tools/probe_client_graph.py",
    'parser.add_argument("--heap-gib", type=int, choices=(6, 8), default=6)',
    'parser.add_argument("--heap-gib", type=int, choices=(4, 5, 6, 8), default=6)',
)
patch(
    "tools/probe_client_graph.py",
    "if args.heap_gib*1024**3 > int(physical.group(1))*0.45 or int(free.group(1)) < (45 if args.heap_gib==8 else 35):",
    "if args.heap_gib*1024**3 > int(physical.group(1))*0.95 or int(free.group(1)) < (45 if args.heap_gib==8 else 35):",
)

print("all patches applied")
