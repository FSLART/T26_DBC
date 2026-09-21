#!/usr/bin/env python3
"""Embed a fingerprint of each DBC file as a #define in its generated header.

For every *.dbc in the repository root (excluding ./old and ./other_dbcs),
computes the SHA256, truncates it to the first 8 bytes (64 bits) and writes a
macro like:

    #define DATA_T26_DBC_SHA256 0x3b9c358f...ULL

into generated/<name>/<name>.h. 64 bits is a strong-enough fingerprint that
fits in a single classic 8-byte CAN frame. The macro is created if missing
and updated in place otherwise.
"""
import hashlib
import os
import re
import sys

DBC_DIR = "."
GENERATED_DIR = "generated"
EXCLUDED_DIRS = {"old", "other_dbcs"}

MARKER = "DBC_SHA256"


def macro_name(base):
    return f"{base.replace('-', '_').upper()}_{MARKER}"


def sha256_of(path):
    h = hashlib.sha256()
    with open(path, "rb") as f:
        for chunk in iter(lambda: f.read(65536), b""):
            h.update(chunk)
    return h.hexdigest()


def add_or_update_define(header_path, name, digest):
    if not os.path.exists(header_path):
        print(f"[SKIP] No generated header: {header_path}")
        return False

    with open(header_path, "r", encoding="utf-8") as f:
        content = f.read()

    value = digest[:16]
    new_line = f"#define {name} 0x{value}ULL"
    old_re = re.compile(rf"^#define {name} 0x[0-9a-fA-F]+ULL$", re.MULTILINE)
    legacy_re = re.compile(rf'^#define {name} ".*?"\n?$', re.MULTILINE)

    # Drop legacy string-form defines (older versions of this script).
    content = legacy_re.sub("", content)

    if old_re.search(content):
        updated = old_re.sub(new_line + "\n", content)
        changed = updated != content
    else:
        anchor = "#include <stddef.h>\n"
        if anchor in content:
            updated = content.replace(
                anchor,
                anchor + "\n/* DBC file integrity. */\n" + new_line + "\n",
                1,
            )
            changed = True
        else:
            print(f"[WARN] Could not find anchor in {header_path}")
            return False

    with open(header_path, "w", encoding="utf-8") as f:
        f.write(updated)
    print(f"[OK] {header_path}: {name} 0x{value}ULL")
    return changed


def main():
    if not os.path.isdir(GENERATED_DIR):
        print(f"[ERROR] {GENERATED_DIR} not found. Run this after cantools "
              "generate_c_source.")
        return 1

    any_changed = False
    for dbc in sorted(os.listdir(DBC_DIR)):
        if not dbc.lower().endswith(".dbc"):
            continue
        if dbc in EXCLUDED_DIRS:
            continue

        base = os.path.splitext(dbc)[0]
        dbc_path = os.path.join(DBC_DIR, dbc)
        header_path = os.path.join(GENERATED_DIR, base, f"{base}.h")

        digest = sha256_of(dbc_path)
        if add_or_update_define(header_path, macro_name(base), digest):
            any_changed = True

    return 0


if __name__ == "__main__":
    sys.exit(main())