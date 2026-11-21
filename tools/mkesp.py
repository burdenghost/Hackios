#!/usr/bin/env python3
"""Lay out an EFI system partition for HakiOS.

The host-side parser is deliberately strict: reject truncated or ambiguous XNUP
payloads before copying anything to a boot volume.
"""
import argparse
import os
import shutil
import struct
import sys

HERE = os.path.dirname(os.path.abspath(__file__))
ROOT = os.path.dirname(HERE)
MAGIC = 0x50554E58                              # "XNUP"
PAYLOAD_LIMIT = 0x04000000 - 0x100000           # payload region less panic-log reserve
HEADER_SIZE = 8
ENTRY_HEADER_SIZE = 24
TEXT_ENTRIES = {"cmdline", "kernel.ver", "physbase", "rdres", "checkpoint", "usb"}


def entries(data):
    """Return {name: bytes}; reject any payload that is not structurally complete."""
    if len(data) < HEADER_SIZE:
        raise ValueError("payload header is truncated")
    magic, size = struct.unpack_from("<II", data)
    if magic != MAGIC:
        raise ValueError("not a payload: it does not start with XNUP")
    if size != len(data) - HEADER_SIZE:
        raise ValueError("declared payload size %d does not match file body %d" %
                         (size, len(data) - HEADER_SIZE))

    end = HEADER_SIZE + size
    out = {}
    at = HEADER_SIZE
    terminated = False
    while at < end:
        if end - at < ENTRY_HEADER_SIZE:
            raise ValueError("truncated entry header at offset %d" % at)
        raw_name = data[at:at + 16]
        length, reserved = struct.unpack_from("<II", data, at + 16)
        if raw_name == b"\0" * 16:
            if data[at:end] != b"\0" * (end - at):
                raise ValueError("malformed payload terminator or trailing bytes")
            if end - at != ENTRY_HEADER_SIZE:
                raise ValueError("payload terminator must be the final 24 bytes")
            terminated = True
            at = end
            break
        if reserved != 0:
            raise ValueError("entry at offset %d has nonzero reserved field" % at)
        if b"\0" not in raw_name:
            raise ValueError("entry name at offset %d is not NUL-terminated" % at)
        name_bytes = raw_name.split(b"\0", 1)[0]
        if any(raw_name[len(name_bytes) + 1:]):
            raise ValueError("entry name at offset %d has nonzero bytes after its NUL" % at)
        try:
            name = name_bytes.decode("ascii")
        except UnicodeDecodeError:
            raise ValueError("entry name at offset %d is not ASCII" % at)
        if not name or name in out or any(ord(c) < 0x20 or ord(c) > 0x7e for c in name):
            raise ValueError("empty, duplicate, or non-printable entry name %r" % name)

        data_at = at + ENTRY_HEADER_SIZE
        padded = (length + 15) & ~15
        next_at = data_at + padded
        if next_at < data_at or next_at > end:
            raise ValueError("entry %r data or padding exceeds payload boundary" % name)
        value_end = data_at + length
        value = data[data_at:value_end]
        if name in TEXT_ENTRIES and b"\0" not in value:
            raise ValueError("text entry %r is not NUL-terminated within its declared size" % name)
        out[name] = value
        at = next_at

    if not terminated:
        raise ValueError("payload has no 24-byte terminator")
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("outdir")
    ap.add_argument("payload", nargs="?", default=os.path.join(ROOT, "qemu", "payload.bin"))
    ap.add_argument("--loader")
    args = ap.parse_args()

    loader = args.loader
    if not loader:
        loader = os.path.join(ROOT, "xnuloader", "loader.efi")
        if not os.path.isfile(loader):
            loader = os.path.join(ROOT, "prebuilt", "loader.efi")
    for what, path in (("loader", loader), ("payload", args.payload)):
        if not os.path.isfile(path):
            sys.exit("mkesp: no %s at %s" % (what, path))
    if os.path.exists(args.outdir) and os.listdir(args.outdir):
        sys.exit("mkesp: %s is not empty" % args.outdir)

    with open(args.payload, "rb") as f:
        data = f.read()
    try:
        parts = entries(data)
    except ValueError as e:
        sys.exit("mkesp: malformed payload: %s" % e)
    if "kernel" not in parts:
        sys.exit("mkesp: the payload has no kernel in it (entries: %s)" %
                 (", ".join(sorted(parts)) or "none"))
    if len(data) > PAYLOAD_LIMIT:
        sys.exit("mkesp: the payload is %d bytes and the loader's payload region holds %d: the root image is too big for "
                 "this way of booting (the big Darwin image goes in over USB, `xl ramdisk`)" %
                 (len(data), PAYLOAD_LIMIT))
    version = parts.get("kernel.ver", b"").split(b"\0", 1)[0].decode("utf-8", errors="replace")
    with open(loader, "rb") as f:
        head = f.read(2)
    if head != b"MZ":
        sys.exit("mkesp: %s is not an EFI application (no MZ)" % loader)

    boot, hakios = (os.path.join(args.outdir, "EFI", d) for d in ("BOOT", "hakios"))
    os.makedirs(boot, exist_ok=True)
    os.makedirs(hakios, exist_ok=True)
    shutil.copyfile(loader, os.path.join(boot, "BOOTAA64.EFI"))
    with open(os.path.join(hakios, "payload.bin"), "wb") as f:
        f.write(data)
    with open(os.path.join(hakios, "kernel.ver"), "w", newline="\n") as f:
        f.write((version or "unknown") + "\n")

    print("mkesp: %s" % args.outdir)
    print("  EFI/BOOT/BOOTAA64.EFI    %9d bytes  the loader" % os.path.getsize(loader))
    print("  EFI/hakios/payload.bin   %9d bytes  %s" %
          (len(data), ", ".join("%s%s" % (k, " (%d)" % len(v) if k != "kernel.ver" else "")
                                for k, v in sorted(parts.items()))))
    print("  kernel.ver=%s" % (version or "unknown (the payload was made with --no-version)"))


if __name__ == "__main__":
    main()
