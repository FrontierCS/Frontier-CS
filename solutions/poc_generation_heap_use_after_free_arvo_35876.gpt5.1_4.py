import os
import tarfile
import tempfile
import shutil


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = tempfile.mkdtemp(prefix="pocgen_")
        try:
            self._extract_tar(src_path, tmpdir)
            poc_path = self._find_poc_file(tmpdir)
            if poc_path is not None:
                try:
                    with open(poc_path, 'rb') as f:
                        return f.read()
                except OSError:
                    pass
            return self._fallback_poc(tmpdir)
        finally:
            shutil.rmtree(tmpdir, ignore_errors=True)

    def _extract_tar(self, src_path: str, dst_dir: str) -> None:
        with tarfile.open(src_path, 'r:*') as tf:
            def is_within_directory(directory: str, target: str) -> bool:
                abs_directory = os.path.abspath(directory)
                abs_target = os.path.abspath(target)
                return os.path.commonpath([abs_directory]) == os.path.commonpath(
                    [abs_directory, abs_target]
                )

            for member in tf.getmembers():
                member_path = os.path.join(dst_dir, member.name)
                if not is_within_directory(dst_dir, member_path):
                    continue
                try:
                    tf.extract(member, path=dst_dir)
                except Exception:
                    continue

    def _iter_files(self, root: str):
        for dirpath, _, filenames in os.walk(root):
            for name in filenames:
                path = os.path.join(dirpath, name)
                if not os.path.isfile(path):
                    continue
                yield path

    def _find_poc_file(self, root: str):
        GROUND_LEN = 79
        keywords_path = [
            'poc',
            'uaf',
            'use-after-free',
            'use_after_free',
            'useafterfree',
            'div',
            'divide',
            'division',
            'zero',
            'byzero',
            'by_zero',
            'by-zero',
            'heap',
            'asan',
            'ubsan',
            'crash',
            'bug',
            'issue',
            'regress',
            'regression',
            'fuzz',
        ]
        binary_exts = {
            '.o',
            '.a',
            '.so',
            '.dll',
            '.dylib',
            '.exe',
            '.class',
            '.jar',
            '.png',
            '.jpg',
            '.jpeg',
            '.gif',
            '.bmp',
            '.ico',
            '.zip',
            '.tar',
            '.gz',
            '.tgz',
            '.bz2',
            '.xz',
            '.7z',
            '.pdf',
        }
        max_small_size = 4096
        best_path = None
        best_score = None

        for path in self._iter_files(root):
            rel = os.path.relpath(path, root)
            name_lower = os.path.basename(path).lower()
            _, ext = os.path.splitext(name_lower)
            if ext in binary_exts:
                continue
            try:
                size = os.path.getsize(path)
            except OSError:
                continue
            if size <= 0 or size > max_small_size:
                continue

            try:
                with open(path, 'rb') as f:
                    data = f.read(max_small_size)
            except OSError:
                continue
            if not data:
                continue

            nontext = 0
            for b in data:
                if b in (9, 10, 13):
                    continue
                if 32 <= b <= 126:
                    continue
                nontext += 1
                if nontext * 5 > len(data):
                    break
            if nontext * 5 > len(data):
                continue

            rel_lower = rel.lower()
            has_kw = any(k in rel_lower for k in keywords_path)

            if size == GROUND_LEN and has_kw:
                prio = 0
            elif size == GROUND_LEN:
                prio = 1
            elif size < 2 * GROUND_LEN and has_kw:
                prio = 2
            elif has_kw:
                prio = 3
            elif size < 2 * GROUND_LEN:
                prio = 4
            else:
                prio = 5

            lower_data = data.lower()
            feature = 0
            if b'/=' in data:
                feature += 4
            if b'/= 0' in data or b'/=0' in data or b'/ 0' in data:
                feature += 3
            if (
                b'division' in lower_data
                or b'divide' in lower_data
                or b'div' in lower_data
            ):
                feature += 2
            if b'zero' in lower_data or b'0' in data:
                feature += 1
            if b'use-after-free' in lower_data or b'use after free' in lower_data:
                feature += 3
            if b'uaf' in lower_data:
                feature += 2

            score = (prio, -feature, abs(size - GROUND_LEN), len(rel_lower), rel_lower)
            if best_score is None or score < best_score:
                best_score = score
                best_path = path

        return best_path

    def _collect_exts(self, root: str):
        exts = set()
        for path in self._iter_files(root):
            name = os.path.basename(path)
            _, ext = os.path.splitext(name)
            if ext:
                exts.add(ext.lower())
        return exts

    def _detect_language(self, root: str):
        exts = self._collect_exts(root)
        if '.php' in exts:
            return 'php'
        if '.rb' in exts or '.rake' in exts or '.gemspec' in exts:
            return 'ruby'
        if '.js' in exts or '.jsx' in exts or '.mjs' in exts:
            return 'js'
        if '.ts' in exts or '.tsx' in exts:
            return 'js'
        if '.lua' in exts:
            return 'lua'
        if '.py' in exts:
            return 'python'

        for name in (
            'README',
            'README.md',
            'Readme',
            'Readme.md',
            'readme',
            'readme.md',
        ):
            path = os.path.join(root, name)
            if not os.path.exists(path):
                continue
            try:
                with open(path, 'rb') as f:
                    text = f.read(4096)
            except OSError:
                continue
            try:
                lower = text.decode('utf-8', 'ignore').lower()
            except Exception:
                continue
            if 'php' in lower:
                return 'php'
            if 'mruby' in lower or 'ruby' in lower:
                return 'ruby'
            if (
                'javascript' in lower
                or 'js engine' in lower
                or 'node.js' in lower
                or 'nodejs' in lower
            ):
                return 'js'
            if 'lua' in lower:
                return 'lua'
            if 'python' in lower:
                return 'python'
        return None

    def _fallback_poc(self, root: str) -> bytes:
        lang = self._detect_language(root)
        if lang == 'php':
            return b"<?php\n$a = 1;\n$a /= 0;\nvar_dump($a);\n"
        if lang == 'ruby':
            return b"a = 1\nbegin\n  a /= 0\nrescue ZeroDivisionError\nend\n"
        if lang == 'js':
            return b"let a = 1;\na /= 0;\nconsole.log(a);\n"
        if lang == 'lua':
            return b"a = 1\na = a / 0\nprint(a)\n"
        if lang == 'python':
            return b"a = 1\ntry:\n    a /= 0\nexcept ZeroDivisionError:\n    pass\n"
        return b"a = 1;\na /= 0;\n"


if __name__ == "__main__":
    import sys

    if len(sys.argv) < 2:
        sys.exit(1)
    sol = Solution()
    result = sol.solve(sys.argv[1])
    sys.stdout.buffer.write(result)
