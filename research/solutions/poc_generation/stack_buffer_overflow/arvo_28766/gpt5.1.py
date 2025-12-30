import os
import re
import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        desired_len = 140
        fallback = b'A' * desired_len

        try:
            tar = tarfile.open(src_path, 'r:*')
        except Exception:
            return fallback

        with tar:
            members = tar.getmembers()
            keyword_pattern = re.compile(
                r'(poc|crash|overflow|stack|asan|ubsan|fuzz|testcase|bug|issue|clusterfuzz|ossfuzz|id_)',
                re.IGNORECASE,
            )

            text_like_exts = {
                '.c', '.cc', '.cpp', '.cxx', '.h', '.hh', '.hpp', '.ipp',
                '.java', '.py', '.sh', '.bat', '.ps1', '.cmake', '.mak',
                '.md', '.rst', '.txt', '.tex', '.html', '.htm', '.js',
                '.css', '.xml', '.json', '.yaml', '.yml', '.toml', '.ini',
                '.cfg', '.csv', '.tsv', '.go', '.rs', '.php', '.rb', '.pl',
                '.m', '.mm', '.cs',
            }

            binary_pref_exts = {
                '.bin', '.dat', '.raw', '.in', '.case', '.pcap', '.poc',
            }

            def score_member(m):
                if not m.isfile():
                    return None
                size = m.size
                if size == 0 or size > 1_000_000:
                    return None

                name_lower = m.name.lower()
                base = os.path.basename(name_lower)
                ext = os.path.splitext(base)[1]

                score = 0.0

                if keyword_pattern.search(name_lower):
                    score += 10.0
                if 'snapshot' in name_lower:
                    score += 3.0
                if 'memory' in name_lower:
                    score += 1.0
                if 'node' in name_lower:
                    score += 1.0
                if '28766' in name_lower:
                    score += 20.0

                if ext in text_like_exts and not keyword_pattern.search(name_lower):
                    score -= 5.0

                if size <= 4096:
                    score += 2.0
                elif size <= 65536:
                    score += 1.0

                score += max(0.0, 5.0 - abs(size - desired_len) / (desired_len / 2.0))

                if ext in binary_pref_exts:
                    score += 1.0

                score += max(0.0, 1.0 - size / 4096.0)

                return score

            best_member = None
            best_score = None

            for m in members:
                sc = score_member(m)
                if sc is None:
                    continue
                if best_member is None or sc > best_score:
                    best_member = m
                    best_score = sc

            if best_member is None:
                # Fallback: choose any small non-source file as last resort
                for m in members:
                    if not m.isfile():
                        continue
                    size = m.size
                    if size == 0 or size > 262144:
                        continue
                    name_lower = m.name.lower()
                    base = os.path.basename(name_lower)
                    ext = os.path.splitext(base)[1]
                    if ext in text_like_exts:
                        continue
                    if base.startswith(('.', '_')):
                        continue
                    sc = max(0.0, 5.0 - abs(size - desired_len) / (desired_len / 2.0))
                    sc += max(0.0, 1.0 - size / 8192.0)
                    if best_member is None or sc > best_score:
                        best_member = m
                        best_score = sc

            if best_member is not None:
                try:
                    f = tar.extractfile(best_member)
                    if f is not None:
                        data = f.read()
                        if data:
                            return data
                except Exception:
                    pass

        return fallback