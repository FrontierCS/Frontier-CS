import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Static PoC: large Python snippet producing a very big AST
        inner = "+".join("1" for _ in range(50))  # 99 chars: 50 digits + 49 '+'
        parts = []
        append = parts.append

        append("x = [\n")
        # 2700 lines, each ~103 bytes -> ~278 KB total
        for _ in range(2700):
            append("(")
            append(inner)
            append("),\n")
        append("0]\n")

        return "".join(parts).encode("utf-8")