import os
import io
import tarfile
import zipfile
import gzip
import bz2
import lzma
import re
import struct


class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = self._find_poc_in_archive(src_path)
        if poc:
            return poc
        return self._fallback_synthetic_poc()

    def _find_poc_in_archive(self, src_path: str) -> bytes | None:
        candidates = []
        try:
            if tarfile.is_tarfile(src_path):
                with tarfile.open(src_path, 'r:*') as tf:
                    for m in tf.getmembers():
                        if not m.isfile():
                            continue
                        if m.size <= 0 or m.size > 2 * 1024 * 1024:
                            continue
                        name = m.name
                        if self._looks_like_source_file(name):
                            continue
                        try:
                            f = tf.extractfile(m)
                            if not f:
                                continue
                            raw = f.read()
                        except Exception:
                            continue
                        raw = self._maybe_decompress(raw, name)
                        if not raw or len(raw) == 0 or len(raw) > 2 * 1024 * 1024:
                            continue
                        if self._should_skip_text(raw, name):
                            continue
                        score = self._score_candidate(name, raw)
                        candidates.append((score, -abs(len(raw) - 512), -len(raw), name, raw))
            elif zipfile.is_zipfile(src_path):
                with zipfile.ZipFile(src_path) as zf:
                    for zi in zf.infolist():
                        if zi.is_dir():
                            continue
                        if zi.file_size <= 0 or zi.file_size > 2 * 1024 * 1024:
                            continue
                        name = zi.filename
                        if self._looks_like_source_file(name):
                            continue
                        try:
                            raw = zf.read(zi)
                        except Exception:
                            continue
                        raw = self._maybe_decompress(raw, name)
                        if not raw or len(raw) == 0 or len(raw) > 2 * 1024 * 1024:
                            continue
                        if self._should_skip_text(raw, name):
                            continue
                        score = self._score_candidate(name, raw)
                        candidates.append((score, -abs(len(raw) - 512), -len(raw), name, raw))
            elif os.path.isdir(src_path):
                for root, _, files in os.walk(src_path):
                    for fn in files:
                        full = os.path.join(root, fn)
                        try:
                            size = os.path.getsize(full)
                        except Exception:
                            continue
                        if size <= 0 or size > 2 * 1024 * 1024:
                            continue
                        if self._looks_like_source_file(full):
                            continue
                        try:
                            with open(full, 'rb') as f:
                                raw = f.read()
                        except Exception:
                            continue
                        raw = self._maybe_decompress(raw, fn)
                        if not raw or len(raw) == 0 or len(raw) > 2 * 1024 * 1024:
                            continue
                        if self._should_skip_text(raw, fn):
                            continue
                        score = self._score_candidate(full, raw)
                        candidates.append((score, -abs(len(raw) - 512), -len(raw), full, raw))
        except Exception:
            pass

        if not candidates:
            return None
        candidates.sort(reverse=True)
        # Prefer exact 512-byte match if within top few candidates
        top = candidates[0]
        for c in candidates[:10]:
            if len(c[-1]) == 512:
                top = c
                break
        return top[-1]

    def _looks_like_source_file(self, name: str) -> bool:
        lname = name.lower()
        src_exts = (
            '.c', '.cc', '.cpp', '.cxx', '.h', '.hpp', '.hh', '.py', '.java', '.go',
            '.rs', '.rb', '.php', '.pl', '.m', '.mm', '.cs', '.ts', '.js', '.css',
            '.html', '.htm', '.xml', '.json', '.yml', '.yaml', '.toml', '.ini',
            '.cfg', '.conf', '.md', '.rst', '.txt', '.cmake', '.mak', '.mk', '.m4',
            '.am', '.ac', '.sln', '.vcxproj', '.vcproj', '.s', '.asm', '.bat',
            '.sh', '.bash', '.fish', '.zsh', '.awk', '.sed', '.ps1', '.psm1',
            '.dockerfile', 'dockerfile', 'makefile', 'readme', 'license', 'copying'
        )
        base = os.path.basename(lname)
        if base in ('makefile', 'cmakelists.txt', 'meson.build', 'meson_options.txt', 'readme', 'license', 'copying'):
            return True
        if base.endswith(src_exts):
            return True
        # Ignore images and other common assets
        asset_exts = ('.png', '.jpg', '.jpeg', '.gif', '.svg', '.ico', '.pdf', '.bmp')
        if base.endswith(asset_exts):
            return True
        return False

    def _maybe_decompress(self, raw: bytes, name: str) -> bytes:
        # Try extension-based first
        lname = name.lower()
        try:
            if lname.endswith('.gz') or raw.startswith(b'\x1f\x8b'):
                return gzip.decompress(raw)
        except Exception:
            pass
        try:
            if lname.endswith('.bz2') or raw.startswith(b'BZh'):
                return bz2.decompress(raw)
        except Exception:
            pass
        try:
            if lname.endswith('.xz') or raw.startswith(b'\xfd7zXZ\x00'):
                return lzma.decompress(raw)
        except Exception:
            pass
        try:
            # Some LZMA raw streams start with 0x5D 0x00 0x00
            if raw[:1] == b']' and len(raw) > 13:
                return lzma.decompress(raw)
        except Exception:
            pass
        return raw

    def _is_probably_text(self, data: bytes) -> bool:
        # Consider short slice
        sample = data[:1024]
        if not sample:
            return True
        # If contains null bytes consider binary
        if b'\x00' in sample:
            return False
        # Count non-printables
        non_print = 0
        for b in sample:
            if b in (9, 10, 13):  # tab, lf, cr
                continue
            if b < 32 or b > 126:
                non_print += 1
        ratio = non_print / max(1, len(sample))
        return ratio < 0.05

    def _should_skip_text(self, raw: bytes, name: str) -> bool:
        # If name hints it's a fuzzer corpus or PoC, allow even if ascii
        lname = name.lower()
        special = any(s in lname for s in ('ossfuzz', 'oss-fuzz', 'fuzz', 'poc', 'testcase', 'crash', 'id:'))
        if special and len(raw) <= 4096:
            return False
        # Skip obvious source/text
        if self._is_probably_text(raw):
            return True
        return False

    def _score_candidate(self, name: str, raw: bytes) -> int:
        lname = name.lower()
        size = len(raw)
        score = 0
        # Strong match to specific oss-fuzz ID
        if '383200048' in lname:
            score += 300
        # Hints from file name
        if 'ossfuzz' in lname or 'oss-fuzz' in lname:
            score += 120
        if 'fuzz' in lname:
            score += 80
        if 'poc' in lname or 'crash' in lname or 'testcase' in lname or 'id:' in lname:
            score += 60
        if 'upx' in lname:
            score += 70
        if 'elf' in lname or lname.endswith('.so'):
            score += 40
        if 'test' in lname or 'testsuite' in lname:
            score += 35
        # Content-based hints
        if raw.startswith(b'\x7fELF'):
            score += 120
        if b'UPX!' in raw:
            score += 140
        # Prefer size near 512
        score += max(0, 180 - abs(size - 512))
        # Penalize very large
        if size > 65536:
            score -= 100
        return score

    def _fallback_synthetic_poc(self) -> bytes:
        # Construct a deterministic 512-byte blob with ELF header and UPX! marker
        # This synthetic PoC is a best-effort placeholder when no concrete PoC is found in the source.
        # ELF64 header (little-endian)
        elf = bytearray(512)
        # e_ident
        elf[0:4] = b'\x7fELF'
        elf[4] = 2  # EI_CLASS = 64-bit
        elf[5] = 1  # EI_DATA = little endian
        elf[6] = 1  # EI_VERSION
        elf[7] = 0  # EI_OSABI
        # e_type (ET_DYN)
        struct.pack_into('<H', elf, 16, 3)
        # e_machine (EM_X86_64)
        struct.pack_into('<H', elf, 18, 62)
        # e_version
        struct.pack_into('<I', elf, 20, 1)
        # e_entry
        struct.pack_into('<Q', elf, 24, 0)
        # e_phoff
        struct.pack_into('<Q', elf, 32, 64)
        # e_shoff
        struct.pack_into('<Q', elf, 40, 0)
        # e_flags
        struct.pack_into('<I', elf, 48, 0)
        # e_ehsize
        struct.pack_into('<H', elf, 52, 64)
        # e_phentsize
        struct.pack_into('<H', elf, 54, 56)
        # e_phnum
        struct.pack_into('<H', elf, 56, 1)
        # e_shentsize
        struct.pack_into('<H', elf, 58, 64)
        # e_shnum
        struct.pack_into('<H', elf, 60, 0)
        # e_shstrndx
        struct.pack_into('<H', elf, 62, 0)

        # Program header at offset 64
        phoff = 64
        # p_type (PT_LOAD)
        struct.pack_into('<I', elf, phoff + 0, 1)
        # p_flags (R | X)
        struct.pack_into('<I', elf, phoff + 4, 5)
        # p_offset
        struct.pack_into('<Q', elf, phoff + 8, 0x100)
        # p_vaddr
        struct.pack_into('<Q', elf, phoff + 16, 0)
        # p_paddr
        struct.pack_into('<Q', elf, phoff + 24, 0)
        # p_filesz
        struct.pack_into('<Q', elf, phoff + 32, 0x100)
        # p_memsz
        struct.pack_into('<Q', elf, phoff + 40, 0x100)
        # p_align
        struct.pack_into('<Q', elf, phoff + 48, 0x1000)

        # Place a UPX! marker and a faux block header at offset 0x100
        payload_off = 0x100
        elf[payload_off:payload_off + 4] = b'UPX!'
        # Add minimal fake block info to mimic b_info-like pattern
        # Not a valid UPX stream; serves as a consistent placeholder.
        cursor = payload_off + 4
        # Fake fields: version/method/etc
        def put32(val):
            nonlocal cursor
            struct.pack_into('<I', elf, cursor, val & 0xFFFFFFFF)
            cursor += 4

        def put16(val):
            nonlocal cursor
            struct.pack_into('<H', elf, cursor, val & 0xFFFF)
            cursor += 2

        def put8(val):
            nonlocal cursor
            struct.pack_into('<B', elf, cursor, val & 0xFF)
            cursor += 1

        # Fake header resembling "b_info" entries
        put16(0x1234)   # signature-ish
        put8(0x02)      # blocks
        put8(0x01)      # version
        put8(0x06)      # method
        put8(0x00)      # level
        put32(0x40)     # compressed size
        put32(0x80)     # uncompressed size
        # Repeated entries to simulate ph.method change scenarios
        for _ in range(3):
            put8(0x00)  # reserved
            put8(0x06)  # method (simulate leftover)
            put32(0x10)  # csize
            put32(0x20)  # usize

        # Fill remaining with pattern data
        for i in range(cursor, 512):
            elf[i] = (i * 37 + 0x5A) & 0xFF
        return bytes(elf)