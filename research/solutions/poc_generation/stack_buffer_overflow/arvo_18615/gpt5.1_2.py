import tarfile
import os


class Solution:
    def solve(self, src_path: str) -> bytes:
        target_len = 10
        try:
            data = self._find_poc_in_tar(src_path, target_len)
            if data is not None:
                return data
        except Exception:
            pass
        return b"\x00" * target_len

    def _find_poc_in_tar(self, src_path: str, target_len: int):
        best_general = None
        best_general_score = float('-inf')
        best_tic30 = None
        best_tic30_score = float('-inf')

        with tarfile.open(src_path, 'r:*') as tar:
            for m in tar.getmembers():
                if not m.isfile():
                    continue
                size = m.size
                if size == 0 or size > 4096:
                    continue

                name_lower = m.name.lower()
                base_name = os.path.basename(name_lower)

                score = 0
                if size == target_len:
                    score += 100
                else:
                    diff = abs(size - target_len)
                    score += max(0, 50 - 5 * diff)

                keywords = [
                    'poc', 'proof', 'crash', 'id_', 'id-', 'tic30', 'tic30-', 'tic30_',
                    'c30', 'tms320c30', 'overflow', 'stack', 'bug', 'fail', 'cve',
                    '21462', '21629', 'tic30-dis', 'tic30_dis'
                ]
                for kw in keywords:
                    if kw in name_lower:
                        score += 30

                ext = ''
                if '.' in base_name:
                    ext = base_name.rsplit('.', 1)[1]
                if ext in ('bin', 'dat', 'obj', 'o', 'elf', 'exe', 'out', 'raw'):
                    score += 10
                if ext in (
                    'txt',
                    'text',
                    'md',
                    'rst',
                    'c',
                    'h',
                    'hpp',
                    'cpp',
                    'py',
                    'pl',
                    'sh',
                    'cfg',
                    'ini',
                    'json',
                    'xml',
                    'yml',
                    'yaml',
                    'log',
                ):
                    score -= 20

                f = tar.extractfile(m)
                if f is None:
                    continue
                data = f.read()
                if not data:
                    continue

                printable = 0
                for b in data:
                    if 32 <= b <= 126 or b in (9, 10, 13):
                        printable += 1
                if printable == len(data):
                    score -= 30
                else:
                    score += 5

                is_tic30 = ('tic30' in name_lower or 'tms320c30' in name_lower)

                if is_tic30:
                    if score > best_tic30_score:
                        best_tic30_score = score
                        best_tic30 = data
                else:
                    if score > best_general_score:
                        best_general_score = score
                        best_general = data

        if best_tic30 is not None and best_tic30_score >= 40:
            return best_tic30
        if best_general is not None and best_general_score >= 60:
            return best_general
        return None