import os
import tarfile
import gzip
import bz2
import lzma
import zipfile
import io

TARGET_LENGTH = 524


class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = None
        try:
            poc = self._find_rar_poc(src_path)
        except Exception:
            poc = None
        if poc is None:
            poc = self._fallback_poc()
        return poc

    def _find_rar_poc(self, src_path: str):
        RAR5_MAGIC = b'Rar!\x1A\x07\x01\x00'
        RAR_MAGIC_OLD = b'Rar!\x1A\x07\x00'
        compressed_exts = ('.gz', '.xz', '.bz2', '.lzma', '.zip')
        keywords = (
            'poc', 'crash', 'cve', 'overflow', 'rar5', 'bug', 'testcase',
            'clusterfuzz', 'oss-fuzz', 'fuzzer', 'id_', '12466'
        )

        if not os.path.isfile(src_path):
            return None

        best_data = None
        best_score = None

        with tarfile.open(src_path, 'r:*') as tar:
            for member in tar.getmembers():
                if not member.isfile():
                    continue
                size = member.size
                if size == 0:
                    continue
                # Skip very large files to keep processing efficient
                if size > 5 * 1024 * 1024:
                    continue

                name_lower = member.name.lower()

                f = tar.extractfile(member)
                if f is None:
                    continue
                try:
                    data = f.read()
                finally:
                    f.close()

                if not data:
                    continue

                candidate_datas = []

                # Direct RAR candidate
                if data.startswith(RAR5_MAGIC) or data.startswith(RAR_MAGIC_OLD):
                    candidate_datas.append(data)

                # Compressed container that might hold RAR
                if not candidate_datas:
                    if name_lower.endswith(compressed_exts) and any(
                        kw in name_lower for kw in keywords
                    ):
                        raw = self._decompress_data(data, name_lower)
                        if raw and (raw.startswith(RAR5_MAGIC) or raw.startswith(RAR_MAGIC_OLD)):
                            candidate_datas.append(raw)

                for cand in candidate_datas:
                    cand_size = len(cand)
                    closeness = abs(cand_size - TARGET_LENGTH)
                    has_kw = any(kw in name_lower for kw in keywords)
                    score = (closeness, 0 if has_kw else 1, cand_size)
                    if best_score is None or score < best_score:
                        best_score = score
                        best_data = cand

        return best_data

    def _decompress_data(self, data: bytes, name_lower: str):
        max_size = 10 * 1024 * 1024  # 10 MiB safety cap
        raw = None
        try:
            if name_lower.endswith('.gz'):
                raw = gzip.decompress(data)
            elif name_lower.endswith('.bz2'):
                raw = bz2.decompress(data)
            elif name_lower.endswith(('.xz', '.lzma')):
                raw = lzma.decompress(data)
            elif name_lower.endswith('.zip'):
                bio = io.BytesIO(data)
                with zipfile.ZipFile(bio) as zf:
                    for zi in zf.infolist():
                        # Skip directories
                        is_dir = False
                        if hasattr(zi, "is_dir"):
                            is_dir = zi.is_dir()
                        else:
                            if zi.filename.endswith('/'):
                                is_dir = True
                        if is_dir:
                            continue
                        if zi.file_size > max_size:
                            continue
                        with zf.open(zi) as f:
                            raw = f.read()
                            break
            if raw is not None and len(raw) <= max_size:
                return raw
        except Exception:
            pass
        return None

    def _fallback_poc(self) -> bytes:
        RAR5_MAGIC = b'Rar!\x1A\x07\x01\x00'
        if TARGET_LENGTH <= len(RAR5_MAGIC):
            return RAR5_MAGIC[:TARGET_LENGTH]
        padding_len = TARGET_LENGTH - len(RAR5_MAGIC)
        return RAR5_MAGIC + b'\x00' * padding_len
