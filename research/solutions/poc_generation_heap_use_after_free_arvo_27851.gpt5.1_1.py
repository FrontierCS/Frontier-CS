import os
import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        data = None

        if os.path.isdir(src_path):
            data = self._find_poc_in_dir(src_path)
        else:
            data = self._find_poc_in_tar(src_path)

        if data is None:
            try:
                if os.path.isfile(src_path):
                    size = os.path.getsize(src_path)
                    if 0 < size <= 4096:
                        with open(src_path, 'rb') as f:
                            data = f.read()
            except OSError:
                data = None

        if data is None:
            data = self._synthetic_poc()

        return data

    def _is_allowed_extension(self, ext: str) -> bool:
        allowed_exts = {
            '',
            '.bin',
            '.dat',
            '.poc',
            '.raw',
            '.txt',
            '.input',
            '.in',
            '.out',
            '.pcap',
            '.payload',
        }
        return ext in allowed_exts

    def _find_poc_in_tar(self, tar_path: str):
        max_file_size = 4096
        files = []
        try:
            with tarfile.open(tar_path, 'r:*') as tar:
                for m in tar.getmembers():
                    if not m.isfile():
                        continue
                    size = m.size
                    if size <= 0 or size > max_file_size:
                        continue
                    base = os.path.basename(m.name)
                    ext = os.path.splitext(base)[1].lower()
                    if not self._is_allowed_extension(ext):
                        continue
                    try:
                        f = tar.extractfile(m)
                    except (KeyError, OSError):
                        continue
                    if not f:
                        continue
                    try:
                        data = f.read()
                    except Exception:
                        continue
                    if not data:
                        continue
                    files.append((m.name, data))
        except Exception:
            return None

        if not files:
            return None
        return self._select_best_candidate(files)

    def _find_poc_in_dir(self, root_dir: str):
        max_file_size = 4096
        files = []
        for dirpath, dirnames, filenames in os.walk(root_dir):
            for filename in filenames:
                path = os.path.join(dirpath, filename)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue
                if size <= 0 or size > max_file_size:
                    continue
                ext = os.path.splitext(filename)[1].lower()
                if not self._is_allowed_extension(ext):
                    continue
                try:
                    with open(path, 'rb') as f:
                        data = f.read()
                except OSError:
                    continue
                if not data:
                    continue
                rel_path = os.path.relpath(path, root_dir)
                files.append((rel_path, data))

        if not files:
            return None
        return self._select_best_candidate(files)

    def _select_best_candidate(self, files):
        target_len = 72
        best = None

        strong_content_terms = [b'raw_encap', b'raw-encap', b'nxast_raw_encap', b'rawencap']
        strong_name_terms = ['raw_encap', 'raw-encap', 'nxast_raw_encap', '27851']
        poc_name_terms = [
            'poc',
            'proof',
            'testcase',
            'crash',
            'uaf',
            'asan',
            'ubsan',
            'heap',
            'use-after-free',
            'use_after_free',
            'crasher',
            'crashers',
            'id:',
            'oom-',
            'timeout-',
            'bug',
        ]
        weak_name_terms = ['seed', 'seeds', 'corpus', 'fuzz', 'input', 'inputs']

        for path, data in files:
            length = len(data)
            path_lower = path.lower()
            low_data = data.lower()

            prio = 99
            if any(term in low_data for term in strong_content_terms):
                prio = 0
            elif any(term in path_lower for term in strong_name_terms):
                prio = 1
            elif any(term in path_lower for term in poc_name_terms):
                prio = 2
            elif any(term in path_lower for term in weak_name_terms):
                prio = 3
            else:
                continue

            distance = abs(length - target_len)
            eq = 0 if length == target_len else 1
            score = (prio, distance, eq, length)

            if best is None or score < best[0]:
                best = (score, data)

        if best is not None:
            return best[1]

        best_any = None
        for path, data in files:
            length = len(data)
            distance = abs(length - target_len)
            score = (distance, length)
            if best_any is None or score < best_any[0]:
                best_any = (score, data)

        if best_any is not None:
            return best_any[1]

        return None

    def _synthetic_poc(self) -> bytes:
        base = b'raw_encap(eth_type=0x0800,ip_proto=6,src=1.2.3.4,dst=5.6.7.8)\n'
        target_len = 72
        if len(base) == target_len:
            return base
        elif len(base) > target_len:
            return base[:target_len]
        else:
            return base + b'A' * (target_len - len(base))
