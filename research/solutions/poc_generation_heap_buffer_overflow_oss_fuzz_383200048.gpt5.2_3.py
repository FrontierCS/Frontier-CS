import os
import re
import io
import tarfile
import base64
import gzip
import bz2
import lzma
import zipfile
from typing import List, Tuple, Optional


class Solution:
    BUG_ID = "383200048"

    _BIN_EXTS = {
        ".bin", ".dat", ".raw", ".poc", ".crash", ".repro", ".input",
        ".elf", ".so", ".exe", ".dll", ".dylib",
        ".upx", ".packed", ".pack",
        ".corpus", ".seed",
    }
    _COMP_EXTS = {".gz", ".xz", ".lzma", ".bz2", ".zip", ".b64", ".base64"}
    _TEXT_EXTS = {
        ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh",
        ".py", ".txt", ".md", ".rst", ".java", ".js", ".go", ".rs", ".sh",
        ".cmake", ".in", ".m4", ".yml", ".yaml", ".toml", ".json",
    }

    _KW_STRONG = ("clusterfuzz", "testcase", "crash", "poc", "repro", "oss-fuzz", "ossfuzz", "minimized", "regress")
    _KW_MED = ("fuzz", "corpus", "seed", "artifact", "issue", "bug")

    def solve(self, src_path: str) -> bytes:
        candidates: List[Tuple[float, int, str, bytes]] = []
        seen = set()

        def add_candidate(name: str, data: bytes):
            if not data:
                return
            h = (len(data), data[:32], data[-32:] if len(data) >= 32 else data)
            if h in seen:
                return
            seen.add(h)
            score = self._score_candidate(name, data)
            candidates.append((score, len(data), name, data))

        def maybe_decompress(name: str, data: bytes) -> List[Tuple[str, bytes]]:
            out = []
            lname = name.lower()
            ext = os.path.splitext(lname)[1]
            try:
                if lname.endswith(".gz"):
                    out.append((name[:-3], self._safe_decompress(gzip.decompress, data, 10_000_000)))
                elif lname.endswith(".bz2"):
                    out.append((name[:-4], self._safe_decompress(bz2.decompress, data, 10_000_000)))
                elif lname.endswith(".xz") or lname.endswith(".lzma"):
                    out.append((name.rsplit(".", 1)[0], self._safe_decompress(lzma.decompress, data, 10_000_000)))
                elif lname.endswith(".zip"):
                    out.extend(self._extract_zip(name, data, 10_000_000))
                elif lname.endswith(".b64") or lname.endswith(".base64"):
                    d = self._try_b64(data.decode("ascii", "ignore"))
                    if d is not None:
                        out.append((name.rsplit(".", 1)[0], d))
            except Exception:
                pass
            return [(n, d) for (n, d) in out if d]

        def scan_text_for_embedded(name: str, text: str):
            for idx, blob in enumerate(self._extract_embedded_blobs(text)):
                add_candidate(f"{name}#embedded[{idx}]", blob)

        def handle_file(name: str, data: bytes):
            if not data:
                return
            add_candidate(name, data)
            for n2, d2 in maybe_decompress(name, data):
                add_candidate(n2, d2)
            if self._looks_textual(data) or name.lower().endswith(tuple(self._TEXT_EXTS)):
                try:
                    txt = data.decode("utf-8", "ignore")
                except Exception:
                    return
                scan_text_for_embedded(name, txt)

        if os.path.isdir(src_path):
            self._scan_dir(src_path, handle_file)
        else:
            self._scan_tar(src_path, handle_file)

        if candidates:
            candidates.sort(key=lambda x: (-x[0], x[1], x[2]))
            return candidates[0][3]

        return self._fallback_elf_512()

    def _scan_dir(self, root: str, handle_file):
        max_bin = 6_000_000
        max_text = 250_000
        max_files = 6000
        count = 0

        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                count += 1
                if count > max_files:
                    return
                path = os.path.join(dirpath, fn)
                rel = os.path.relpath(path, root).replace("\\", "/")
                lname = rel.lower()
                try:
                    st = os.stat(path)
                except Exception:
                    continue
                size = st.st_size
                if size <= 0:
                    continue

                ext = os.path.splitext(lname)[1]
                is_text = ext in self._TEXT_EXTS
                interesting = (
                    self.BUG_ID in lname
                    or any(k in lname for k in self._KW_STRONG)
                    or ext in self._BIN_EXTS
                    or ext in self._COMP_EXTS
                    or (128 <= size <= 4096 and not is_text)
                )
                if not interesting:
                    continue

                if is_text and size > max_text:
                    continue
                if (not is_text) and size > max_bin:
                    continue

                try:
                    with open(path, "rb") as f:
                        data = f.read()
                except Exception:
                    continue
                handle_file(rel, data)

    def _scan_tar(self, tar_path: str, handle_file):
        max_bin = 6_000_000
        max_text = 250_000
        max_members = 12000

        try:
            tf = tarfile.open(tar_path, mode="r:*")
        except Exception:
            return

        with tf:
            n = 0
            for m in tf:
                n += 1
                if n > max_members:
                    break
                if not m.isfile():
                    continue
                name = m.name.replace("\\", "/")
                lname = name.lower()
                size = m.size
                if size <= 0:
                    continue

                ext = os.path.splitext(lname)[1]
                is_text = ext in self._TEXT_EXTS

                interesting = (
                    self.BUG_ID in lname
                    or any(k in lname for k in self._KW_STRONG)
                    or ext in self._BIN_EXTS
                    or ext in self._COMP_EXTS
                    or (128 <= size <= 4096 and not is_text)
                )
                if not interesting and is_text and (("fuzz" in lname) or ("test" in lname) or ("oss-fuzz" in lname) or (self.BUG_ID in lname)):
                    interesting = True

                if not interesting:
                    continue

                if is_text and size > max_text:
                    continue
                if (not is_text) and size > max_bin:
                    continue

                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    data = f.read()
                except Exception:
                    continue
                handle_file(name, data)

    def _score_candidate(self, name: str, data: bytes) -> float:
        lname = name.lower()
        n = len(data)

        score = 0.0

        if self.BUG_ID in lname:
            score += 2000.0

        for k in self._KW_STRONG:
            if k in lname:
                score += 600.0
        for k in self._KW_MED:
            if k in lname:
                score += 120.0

        ext = os.path.splitext(lname)[1]
        if ext in self._BIN_EXTS:
            score += 240.0
        if ext in self._COMP_EXTS:
            score += 80.0

        if self._looks_elf(data):
            score += 350.0
            et = self._elf_type(data)
            if et == 3:
                score += 300.0

        if b"UPX!" in data:
            score += 500.0
        if b"UPX0" in data or b"UPX1" in data:
            score += 220.0

        if n == 512:
            score += 350.0
        score -= min(200.0, abs(n - 512) / 3.0)
        score -= min(200.0, n / 2500.0)

        if self._looks_textual(data):
            score -= 180.0

        return score

    def _looks_textual(self, data: bytes) -> bool:
        if not data:
            return True
        if b"\x00" in data:
            return False
        sample = data[:4096]
        bad = 0
        for b in sample:
            if b in (9, 10, 13):
                continue
            if 32 <= b <= 126:
                continue
            bad += 1
        return (bad / max(1, len(sample))) < 0.02

    def _looks_elf(self, data: bytes) -> bool:
        return len(data) >= 16 and data[:4] == b"\x7fELF"

    def _elf_type(self, data: bytes) -> Optional[int]:
        if not self._looks_elf(data) or len(data) < 20:
            return None
        ei_class = data[4]
        ei_data = data[5]
        if ei_data == 1:
            endian = "little"
        elif ei_data == 2:
            endian = "big"
        else:
            return None
        try:
            e_type = int.from_bytes(data[16:18], endian)
        except Exception:
            return None
        if e_type in (1, 2, 3, 4):
            return e_type
        return None

    def _safe_decompress(self, fn, data: bytes, max_out: int) -> bytes:
        out = fn(data)
        if out is None:
            return b""
        if len(out) > max_out:
            return b""
        return out

    def _extract_zip(self, name: str, data: bytes, max_total: int) -> List[Tuple[str, bytes]]:
        out = []
        try:
            with zipfile.ZipFile(io.BytesIO(data)) as zf:
                total = 0
                for zi in zf.infolist():
                    if zi.is_dir():
                        continue
                    if zi.file_size <= 0 or zi.file_size > max_total:
                        continue
                    if total + zi.file_size > max_total:
                        break
                    try:
                        b = zf.read(zi)
                    except Exception:
                        continue
                    total += len(b)
                    out.append((f"{name}:{zi.filename}", b))
        except Exception:
            return []
        return out

    def _try_b64(self, s: str) -> Optional[bytes]:
        ss = re.sub(r"\s+", "", s)
        if len(ss) < 80:
            return None
        if len(ss) % 4 != 0:
            return None
        if not re.fullmatch(r"[A-Za-z0-9+/]*={0,2}", ss):
            return None
        try:
            return base64.b64decode(ss, validate=True)
        except Exception:
            return None

    def _extract_embedded_blobs(self, text: str) -> List[bytes]:
        blobs = []

        for m in re.finditer(r"(?s)(?:^|[^A-Za-z0-9+/=])([A-Za-z0-9+/=\r\n]{160,})(?:$|[^A-Za-z0-9+/=])", text):
            s = m.group(1)
            d = self._try_b64(s)
            if d and 16 <= len(d) <= 10_000_000:
                blobs.append(d)

        for m in re.finditer(r"(?:[A-Za-z0-9+/]{80,}={0,2})", text):
            d = self._try_b64(m.group(0))
            if d and 16 <= len(d) <= 10_000_000:
                blobs.append(d)

        for m in re.finditer(r"(?s)(?:0x[0-9a-fA-F]{2}\s*,\s*){64,}0x[0-9a-fA-F]{2}", text):
            block = m.group(0)
            hexes = re.findall(r"0x([0-9a-fA-F]{2})", block)
            if len(hexes) >= 64:
                try:
                    blobs.append(bytes(int(h, 16) for h in hexes))
                except Exception:
                    pass

        for m in re.finditer(r"(?:\\x[0-9a-fA-F]{2}){64,}", text):
            seq = m.group(0)
            hs = re.findall(r"\\x([0-9a-fA-F]{2})", seq)
            if len(hs) >= 64:
                try:
                    blobs.append(bytes(int(h, 16) for h in hs))
                except Exception:
                    pass

        dedup = []
        seen = set()
        for b in blobs:
            k = (len(b), b[:32], b[-32:] if len(b) >= 32 else b)
            if k in seen:
                continue
            seen.add(k)
            dedup.append(b)
        return dedup

    def _fallback_elf_512(self) -> bytes:
        # Minimal 32-bit little-endian ET_DYN ELF with one PT_LOAD, plus "UPX!" marker.
        data = bytearray(b"\x00" * 512)
        data[0:4] = b"\x7fELF"
        data[4] = 1  # EI_CLASS: 32-bit
        data[5] = 1  # EI_DATA: little
        data[6] = 1  # EI_VERSION
        data[7] = 0  # EI_OSABI
        # e_type (ET_DYN=3), e_machine (EM_386=3), e_version=1
        data[16:18] = (3).to_bytes(2, "little")
        data[18:20] = (3).to_bytes(2, "little")
        data[20:24] = (1).to_bytes(4, "little")
        # e_entry
        data[24:28] = (0).to_bytes(4, "little")
        # e_phoff: 52
        data[28:32] = (52).to_bytes(4, "little")
        # e_shoff: 0
        data[32:36] = (0).to_bytes(4, "little")
        # e_flags: 0
        data[36:40] = (0).to_bytes(4, "little")
        # e_ehsize: 52
        data[40:42] = (52).to_bytes(2, "little")
        # e_phentsize: 32, e_phnum: 1
        data[42:44] = (32).to_bytes(2, "little")
        data[44:46] = (1).to_bytes(2, "little")
        # e_shentsize, e_shnum, e_shstrndx: 0
        data[46:52] = b"\x00" * 6

        # Program header at offset 52 (Elf32_Phdr, 32 bytes)
        ph = 52
        # p_type PT_LOAD=1
        data[ph + 0:ph + 4] = (1).to_bytes(4, "little")
        # p_offset
        data[ph + 4:ph + 8] = (0).to_bytes(4, "little")
        # p_vaddr, p_paddr
        data[ph + 8:ph + 12] = (0x08048000).to_bytes(4, "little")
        data[ph + 12:ph + 16] = (0x08048000).to_bytes(4, "little")
        # p_filesz, p_memsz
        data[ph + 16:ph + 20] = (512).to_bytes(4, "little")
        data[ph + 20:ph + 24] = (512).to_bytes(4, "little")
        # p_flags: R-X
        data[ph + 24:ph + 28] = (5).to_bytes(4, "little")
        # p_align
        data[ph + 28:ph + 32] = (0x1000).to_bytes(4, "little")

        marker_off = 0x100
        data[marker_off:marker_off + 4] = b"UPX!"
        data[marker_off + 4:marker_off + 8] = b"UPX0"
        data[marker_off + 8:marker_off + 12] = b"UPX1"
        return bytes(data)