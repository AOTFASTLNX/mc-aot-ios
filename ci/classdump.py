"""Print the field access flags of one class inside a jar (no ASM needed)."""

import struct
import sys
import zipfile

ACC_NAMES = [
    (0x0001, "public"), (0x0002, "private"), (0x0004, "protected"),
    (0x0008, "static"), (0x0010, "final"), (0x0020, "synchronized/super"),
    (0x0040, "volatile/bridge"), (0x0080, "transient/varargs"),
    (0x0100, "native"), (0x0200, "interface"), (0x0400, "abstract"),
]


def flags(value: int) -> str:
    names = [name for bit, name in ACC_NAMES if value & bit]
    return f"0x{value:04x} ({' '.join(names)})"


def parse(data: bytes):
    offset = 8
    count = struct.unpack_from(">H", data, offset)[0]
    offset += 2
    pool = [None] * count
    index = 1
    while index < count:
        tag = data[offset]
        offset += 1
        if tag == 1:
            length = struct.unpack_from(">H", data, offset)[0]
            offset += 2
            pool[index] = data[offset:offset + length].decode("utf-8", "replace")
            offset += length
        elif tag in (7, 8, 16, 19, 20):
            offset += 2
        elif tag in (15,):
            offset += 3
        elif tag in (3, 4, 9, 10, 11, 12, 17, 18):
            offset += 4
        elif tag in (5, 6):
            offset += 8
            index += 1
        else:
            raise SystemExit(f"unknown constant pool tag {tag}")
        index += 1

    access, this_class, _super = struct.unpack_from(">HHH", data, offset)
    offset += 6
    interfaces = struct.unpack_from(">H", data, offset)[0]
    offset += 2 + interfaces * 2
    fields = struct.unpack_from(">H", data, offset)[0]
    offset += 2
    print(f"class {pool[pool[this_class]]} flags {flags(access)} fields={fields}")
    for _ in range(fields):
        f_access, f_name, _f_desc, attrs = struct.unpack_from(">HHHH", data, offset)
        offset += 8
        for _ in range(attrs):
            _name, length = struct.unpack_from(">HI", data, offset)
            offset += 6 + length
        print(f"  {pool[f_name]:40s} {flags(f_access)}")


def main() -> int:
    jar, wanted = sys.argv[1], sys.argv[2]
    with zipfile.ZipFile(jar) as archive:
        for name in archive.namelist():
            if name.endswith(".class") and wanted in name:
                print(f"-- {jar}: {name}")
                parse(archive.read(name))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
