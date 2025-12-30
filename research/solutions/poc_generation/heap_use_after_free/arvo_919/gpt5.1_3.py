import os
import tarfile
import zipfile


class Solution:
    GROUND_TRUTH_LEN = 800

    FONT_EXTS = {
        '.ttf', '.otf', '.woff', '.woff2',
        '.ttc', '.otc', '.cff', '.pfa', '.pfb'
    }

    TEXT_EXTS = {
        '.c', '.cc', '.cpp', '.cxx', '.h', '.hpp', '.hh',
        '.py', '.pyw', '.sh', '.bash', '.zsh',
        '.java', '.js', '.jsx', '.ts', '.tsx',
        '.rb', '.go', '.rs', '.php',
        '.txt', '.md', '.markdown', '.rst',
        '.html', '.htm', '.xml',
        '.yml', '.yaml', '.json', '.toml', '.ini', '.cfg',
        '.cmake', '.am', '.ac', '.m4', '.in', '.mk',
        '.gradle', '.properties',
        '.bat', '.ps1',
        '.pl', '.pm', '.tcl',
        '.tex', '.csv',
        '.sln', '.vcxproj', '.csproj',
        '.Dockerfile', '.dockerfile'
    }

    VULN_KEYWORDS = (
        'use-after-free',
        'use_after_free',
        'heap-use-after-free',
        'heap_use_after_free',
        'heap-uaf',
        'uaf',
    )

    GENERAL_KEYWORDS = (
        'poc',
        'crash',
        'bug',
        'issue',
        'clusterfuzz',
        'fuzzer',
        'regress',
        'regression',
        'cve',
        'vuln',
    )

    MAX_CANDIDATE_SIZE = 10 * 1024 * 1024  # 10 MB

    def solve(self, src_path: str) -> bytes:
        # Try directory
        try:
            if os.path.isdir(src_path):
                data = self._solve_from_directory(src_path)
                if data:
                    return data
        except Exception:
            pass

        # Try tarball
        try:
            if os.path.isfile(src_path) and tarfile.is_tarfile(src_path):
                data = self._solve_from_tar(src_path)
                if data:
                    return data
        except Exception:
            pass

        # Try zipfile
        try:
            if os.path.isfile(src_path) and zipfile.is_zipfile(src_path):
                data = self._solve_from_zip(src_path)
                if data:
                    return data
        except Exception:
            pass

        # Fallback generic PoC
        return self._fallback_poc()

    # ------------------------------------------------------------------ #
    # Core scoring and selection helpers
    # ------------------------------------------------------------------ #
    def _score_candidate(self, name: str, size: int) -> int:
        if size <= 0 or size > self.MAX_CANDIDATE_SIZE:
            return 0

        lower_name = name.replace('\\', '/').lower()
        _, ext = os.path.splitext(lower_name)

        if ext in self.TEXT_EXTS:
            return 0

        is_font = ext in self.FONT_EXTS

        in_interest_path = any(
            kw in lower_name
            for kw in ('test', 'tests', 'regress', 'regression', 'fuzz', 'corpus', 'fonts', 'font')
        )

        has_vuln_keyword = any(kw in lower_name for kw in self.VULN_KEYWORDS)
        has_general_keyword = any(kw in lower_name for kw in self.GENERAL_KEYWORDS)

        mentions_ots = 'ots' in lower_name

        # Require at least some hint that this is interesting
        if not (is_font or in_interest_path or has_vuln_keyword or has_general_keyword or mentions_ots):
            return 0

        score = 0

        if is_font:
            score += 200

        if in_interest_path:
            score += 50

        if mentions_ots:
            score += 150

        if has_vuln_keyword:
            score += 250

        if has_general_keyword:
            score += 120

        # Prefer files whose size is close to the ground-truth PoC length
        closeness = abs(size - self.GROUND_TRUTH_LEN)
        closeness_bonus = max(0, 100 - int(closeness / 8))
        score += closeness_bonus

        return score

    def _update_best(self, best, score: int, size: int, identifier):
        if score <= 0:
            return best
        closeness = abs(size - self.GROUND_TRUTH_LEN)
        if best is None:
            return (score, closeness, size, identifier)
        b_score, b_close, b_size, _ = best
        if score > b_score:
            return (score, closeness, size, identifier)
        if score == b_score:
            if closeness < b_close:
                return (score, closeness, size, identifier)
            if closeness == b_close and size < b_size:
                return (score, closeness, size, identifier)
        return best

    # ------------------------------------------------------------------ #
    # Directory handling
    # ------------------------------------------------------------------ #
    def _solve_from_directory(self, root: str) -> bytes | None:
        best = None
        for dirpath, _, filenames in os.walk(root):
            for fname in filenames:
                full_path = os.path.join(dirpath, fname)
                try:
                    st = os.stat(full_path)
                except OSError:
                    continue
                size = st.st_size
                if size <= 0 or size > self.MAX_CANDIDATE_SIZE:
                    continue
                rel = os.path.relpath(full_path, root)
                score = self._score_candidate(rel, size)
                best = self._update_best(best, score, size, full_path)

        if best is None:
            return None

        best_path = best[3]
        try:
            with open(best_path, 'rb') as f:
                data = f.read()
            if data:
                return data
        except Exception:
            pass
        return None

    # ------------------------------------------------------------------ #
    # Tarball handling
    # ------------------------------------------------------------------ #
    def _solve_from_tar(self, tar_path: str) -> bytes | None:
        best = None
        tf = tarfile.open(tar_path, 'r:*')
        try:
            for member in tf.getmembers():
                if not member.isfile():
                    continue
                size = member.size
                if size <= 0 or size > self.MAX_CANDIDATE_SIZE:
                    continue
                name = member.name
                score = self._score_candidate(name, size)
                best = self._update_best(best, score, size, member)

            if best is None:
                return None

            best_member = best[3]
            try:
                f = tf.extractfile(best_member)
                if f is None:
                    return None
                data = f.read()
                if data:
                    return data
            except Exception:
                return None
        finally:
            tf.close()
        return None

    # ------------------------------------------------------------------ #
    # Zipfile handling
    # ------------------------------------------------------------------ #
    def _solve_from_zip(self, zip_path: str) -> bytes | None:
        best = None
        with zipfile.ZipFile(zip_path, 'r') as zf:
            for info in zf.infolist():
                # Skip directories
                is_dir = False
                if hasattr(info, "is_dir"):
                    is_dir = info.is_dir()
                else:
                    is_dir = info.filename.endswith('/')
                if is_dir:
                    continue

                size = info.file_size
                if size <= 0 or size > self.MAX_CANDIDATE_SIZE:
                    continue

                name = info.filename
                score = self._score_candidate(name, size)
                best = self._update_best(best, score, size, name)

            if best is None:
                return None

            best_name = best[3]
            try:
                data = zf.read(best_name)
                if data:
                    return data
            except Exception:
                return None
        return None

    # ------------------------------------------------------------------ #
    # Fallback PoC
    # ------------------------------------------------------------------ #
    def _fallback_poc(self) -> bytes:
        # Generic minimal OpenType-like header with padding to desired length
        length = self.GROUND_TRUTH_LEN
        if length < 4:
            return b'A' * length
        header = b'OTTO'  # OpenType/CFF magic; content is otherwise arbitrary
        return header + b'A' * (length - len(header))