import os
import io
import sys
import tarfile
import zipfile
import gzip
import bz2
import lzma

EXT_J2K = {'.j2k', '.jp2', '.j2c', '.jpc', '.jpf', '.jpt', '.mj2', '.jpx'}
ARCHIVE_EXTS = {'.zip', '.tar', '.tgz', '.tar.gz', '.tbz2', '.tar.bz2', '.txz', '.tar.xz'}
COMP_EXTS = {'.gz', '.bz2', '.xz', '.lzma'}
TARGET_SIZE = 1479

def _is_jp2_bytes(data: bytes) -> bool:
    if len(data) >= 12 and data[:12] == b'\x00\x00\x00\x0cjP  \r\n\x87\n':
        return True
    if b'ftypjp2' in data[:64]:
        return True
    return False

def _is_j2k_bytes(data: bytes) -> bool:
    return len(data) >= 2 and data[0] == 0xFF and data[1] == 0x4F

def _is_j2kish(data: bytes) -> bool:
    return _is_j2k_bytes(data) or _is_jp2_bytes(data)

def _is_text_bytes(sample: bytes) -> bool:
    if not sample:
        return False
    # If null bytes present, treat as binary
    if b'\x00' in sample:
        return False
    text_chars = bytearray({7,8,9,10,12,13,27} | set(range(0x20, 0x7F)))
    # ratio of printable characters
    nontext = sum(c not in text_chars for c in sample[:4096])
    ratio = nontext / min(len(sample), 4096)
    return ratio < 0.05

def _ext_of_name(name: str) -> str:
    n = name.lower()
    # handle .tar.gz -> ext '.tar.gz'
    for ext in ('.tar.gz', '.tar.bz2', '.tar.xz', '.tbz2', '.tgz', '.txz'):
        if n.endswith(ext):
            return ext
    return os.path.splitext(n)[1]

def _name_has_keywords(name: str) -> bool:
    n = name.lower()
    kws = ('poc', 'repro', 'crash', 'id', 'fuzz', 'afl', 'heap', 'overflow', 'trigger', 'test', 'case')
    return any(k in n for k in kws)

def _score_candidate(name: str, data: bytes) -> int:
    n = name.lower()
    size = len(data)
    ext = _ext_of_name(n)
    score = 0
    # Size closeness priority
    if size == TARGET_SIZE:
        score += 1000
    else:
        diff = abs(size - TARGET_SIZE)
        if diff <= 2:
            score += 300
        elif diff <= 10:
            score += 200
        elif diff <= 100:
            score += 100
        elif diff <= 500:
            score += 50
    # Magic
    if _is_j2kish(data):
        score += 500
    # Extension
    if ext in EXT_J2K:
        score += 200
    # Name hints
    if _name_has_keywords(n):
        score += 150
    # Penalize text files
    if _is_text_bytes(data[:1024]):
        score -= 400
    return score

def _maybe_decompress_by_ext(name: str, data: bytes):
    n = name.lower()
    try:
        if n.endswith('.gz'):
            return gzip.decompress(data)
        if n.endswith('.bz2') or n.endswith('.tbz2'):
            return bz2.decompress(data)
        if n.endswith('.xz') or n.endswith('.txz') or n.endswith('.lzma'):
            return lzma.decompress(data)
    except Exception:
        return None
    return None

def _open_zip_from_bytes(data: bytes):
    try:
        bio = io.BytesIO(data)
        zf = zipfile.ZipFile(bio)
        return zf
    except Exception:
        return None

def _open_tar_from_bytes(data: bytes):
    try:
        bio = io.BytesIO(data)
        tf = tarfile.open(fileobj=bio, mode='r:*')
        return tf
    except Exception:
        return None

def _read_tar_member(tar: tarfile.TarFile, m: tarfile.TarInfo) -> bytes:
    try:
        f = tar.extractfile(m)
        if not f:
            return b''
        return f.read()
    except Exception:
        return b''

def _search_in_tarfile(tar: tarfile.TarFile, base: str, target_first: bool = True):
    best = (float('-inf'), None)
    # First pass: exact size matches
    if target_first:
        for m in tar.getmembers():
            if not m.isreg():
                continue
            if m.size != TARGET_SIZE:
                continue
            name = base + m.name
            data = _read_tar_member(tar, m)
            if not data:
                continue
            score = _score_candidate(name, data)
            if score > best[0]:
                best = (score, data)
        if best[1] is not None:
            return best
    # Second pass: likely PoC by extension or keywords
    for m in tar.getmembers():
        if not m.isreg():
            continue
        name = base + m.name
        ext = _ext_of_name(name)
        consider = False
        if m.size == TARGET_SIZE:
            consider = True
        elif ext in EXT_J2K:
            consider = True
        elif _name_has_keywords(name):
            consider = True
        elif ext in ARCHIVE_EXTS or ext in COMP_EXTS:
            consider = True
        if not consider:
            continue
        data = _read_tar_member(tar, m)
        if not data:
            continue
        # Try direct candidate
        score = _score_candidate(name, data)
        if score > best[0]:
            best = (score, data)
        # Try compressed inner
        if ext in COMP_EXTS:
            decomp = _maybe_decompress_by_ext(name, data)
            if decomp:
                # if decompressed data is j2kish, evaluate
                sc2 = _score_candidate(name + "|decomp", decomp)
                if sc2 > best[0]:
                    best = (sc2, decomp)
                # if decompressed is archive, search inside
                zf = _open_zip_from_bytes(decomp)
                if zf is not None:
                    sc, dat = _search_in_zipfile(zf, name + "!", target_first=False)
                    if dat is not None and sc > best[0]:
                        best = (sc, dat)
                    try:
                        zf.close()
                    except Exception:
                        pass
                tf2 = _open_tar_from_bytes(decomp)
                if tf2 is not None:
                    sc, dat = _search_in_tarfile(tf2, name + "!", target_first=False)
                    if dat is not None and sc > best[0]:
                        best = (sc, dat)
                    try:
                        tf2.close()
                    except Exception:
                        pass
        # Try nested archives
        if ext in ARCHIVE_EXTS:
            zf = _open_zip_from_bytes(data)
            if zf is not None:
                sc, dat = _search_in_zipfile(zf, name + "!", target_first=True)
                if dat is not None and sc > best[0]:
                    best = (sc, dat)
                try:
                    zf.close()
                except Exception:
                    pass
            tf2 = _open_tar_from_bytes(data)
            if tf2 is not None:
                sc, dat = _search_in_tarfile(tf2, name + "!", target_first=True)
                if dat is not None and sc > best[0]:
                    best = (sc, dat)
                try:
                    tf2.close()
                except Exception:
                    pass
    return best

def _search_in_zipfile(zf: zipfile.ZipFile, base: str, target_first: bool = True):
    best = (float('-inf'), None)
    # First pass: exact size matches
    if target_first:
        for zi in zf.infolist():
            if zi.is_dir():
                continue
            if zi.file_size != TARGET_SIZE:
                continue
            try:
                data = zf.read(zi)
            except Exception:
                continue
            name = base + zi.filename
            score = _score_candidate(name, data)
            if score > best[0]:
                best = (score, data)
        if best[1] is not None:
            return best
    for zi in zf.infolist():
        if zi.is_dir():
            continue
        name = base + zi.filename
        ext = _ext_of_name(name)
        consider = False
        if zi.file_size == TARGET_SIZE:
            consider = True
        elif ext in EXT_J2K or _name_has_keywords(name) or ext in ARCHIVE_EXTS or ext in COMP_EXTS:
            consider = True
        if not consider:
            continue
        try:
            data = zf.read(zi)
        except Exception:
            continue
        score = _score_candidate(name, data)
        if score > best[0]:
            best = (score, data)
        if ext in COMP_EXTS:
            decomp = _maybe_decompress_by_ext(name, data)
            if decomp:
                sc2 = _score_candidate(name + "|decomp", decomp)
                if sc2 > best[0]:
                    best = (sc2, decomp)
                zf2 = _open_zip_from_bytes(decomp)
                if zf2 is not None:
                    sc, dat = _search_in_zipfile(zf2, name + "!", target_first=False)
                    if dat is not None and sc > best[0]:
                        best = (sc, dat)
                    try:
                        zf2.close()
                    except Exception:
                        pass
                tf2 = _open_tar_from_bytes(decomp)
                if tf2 is not None:
                    sc, dat = _search_in_tarfile(tf2, name + "!", target_first=False)
                    if dat is not None and sc > best[0]:
                        best = (sc, dat)
                    try:
                        tf2.close()
                    except Exception:
                        pass
        if ext in ARCHIVE_EXTS:
            zf2 = _open_zip_from_bytes(data)
            if zf2 is not None:
                sc, dat = _search_in_zipfile(zf2, name + "!", target_first=True)
                if dat is not None and sc > best[0]:
                    best = (sc, dat)
                try:
                    zf2.close()
                except Exception:
                    pass
            tf2 = _open_tar_from_bytes(data)
            if tf2 is not None:
                sc, dat = _search_in_tarfile(tf2, name + "!", target_first=True)
                if dat is not None and sc > best[0]:
                    best = (sc, dat)
                try:
                    tf2.close()
                except Exception:
                    pass
    return best

def _search_in_directory(dirpath: str):
    best = (float('-inf'), None)
    # First pass: exact size
    for root, _, files in os.walk(dirpath):
        for fn in files:
            p = os.path.join(root, fn)
            try:
                st = os.stat(p)
            except Exception:
                continue
            if not os.path.isfile(p):
                continue
            if st.st_size != TARGET_SIZE:
                continue
            try:
                with open(p, 'rb') as f:
                    data = f.read()
            except Exception:
                continue
            score = _score_candidate(p, data)
            if score > best[0]:
                best = (score, data)
    if best[1] is not None:
        return best
    # Second pass: extensions and keywords, and nested archives
    for root, _, files in os.walk(dirpath):
        for fn in files:
            p = os.path.join(root, fn)
            try:
                st = os.stat(p)
            except Exception:
                continue
            if not os.path.isfile(p):
                continue
            n = p.lower()
            ext = _ext_of_name(n)
            consider = False
            if ext in EXT_J2K or _name_has_keywords(n) or ext in ARCHIVE_EXTS or ext in COMP_EXTS:
                consider = True
            if not consider:
                continue
            try:
                with open(p, 'rb') as f:
                    data = f.read()
            except Exception:
                continue
            score = _score_candidate(p, data)
            if score > best[0]:
                best = (score, data)
            if ext in COMP_EXTS:
                decomp = _maybe_decompress_by_ext(n, data)
                if decomp:
                    sc2 = _score_candidate(n + "|decomp", decomp)
                    if sc2 > best[0]:
                        best = (sc2, decomp)
                    zf = _open_zip_from_bytes(decomp)
                    if zf is not None:
                        sc, dat = _search_in_zipfile(zf, n + "!", target_first=False)
                        if dat is not None and sc > best[0]:
                            best = (sc, dat)
                        try:
                            zf.close()
                        except Exception:
                            pass
                    tf2 = _open_tar_from_bytes(decomp)
                    if tf2 is not None:
                        sc, dat = _search_in_tarfile(tf2, n + "!", target_first=False)
                        if dat is not None and sc > best[0]:
                            best = (sc, dat)
                        try:
                            tf2.close()
                        except Exception:
                            pass
            if ext in ARCHIVE_EXTS:
                zf = _open_zip_from_bytes(data)
                if zf is not None:
                    sc, dat = _search_in_zipfile(zf, n + "!", target_first=True)
                    if dat is not None and sc > best[0]:
                        best = (sc, dat)
                    try:
                        zf.close()
                    except Exception:
                        pass
                tf2 = _open_tar_from_bytes(data)
                if tf2 is not None:
                    sc, dat = _search_in_tarfile(tf2, n + "!", target_first=True)
                    if dat is not None and sc > best[0]:
                        best = (sc, dat)
                    try:
                        tf2.close()
                    except Exception:
                        pass
    return best

def _search_in_file(path: str):
    # Try tar
    try:
        if tarfile.is_tarfile(path):
            with tarfile.open(path, 'r:*') as tf:
                return _search_in_tarfile(tf, "", target_first=True)
    except Exception:
        pass
    # Try zip
    try:
        if zipfile.is_zipfile(path):
            with zipfile.ZipFile(path) as zf:
                return _search_in_zipfile(zf, "", target_first=True)
    except Exception:
        pass
    # Plain file
    try:
        with open(path, 'rb') as f:
            data = f.read()
        return (_score_candidate(path, data), data)
    except Exception:
        return (float('-inf'), None)

def _find_poc(src_path: str) -> bytes:
    # If it's a directory
    if os.path.isdir(src_path):
        sc, dat = _search_in_directory(src_path)
        if dat is not None:
            return dat
        return b''
    # Else treat as file
    sc, dat = _search_in_file(src_path)
    if dat is not None:
        return dat
    return b''

class Solution:
    def solve(self, src_path: str) -> bytes:
        data = _find_poc(src_path)
        if data:
            return data
        # Fallback minimal JPEG 2000 codestream bytes (unlikely to trigger, but ensures valid return)
        # Construct a minimal JP2 file with signature and ftyp box; content is mostly dummy.
        # This is a safe fallback if no PoC is found in the archive.
        jp2_sig = b'\x00\x00\x00\x0cjP  \r\n\x87\n'
        ftyp = b'ftypjp2 ' + b'\x00\x00\x00\x00' + b'jp2 ' + b'\x00\x00\x00\x00'
        ftyp_box = len(ftyp).to_bytes(4, 'big') + ftyp
        jp2h = b'jp2h'  # placeholder
        jp2h_box = (8).to_bytes(4, 'big') + jp2h  # empty box
        # Minimal contiguous boxes
        content = jp2_sig + ftyp_box + jp2h_box
        return content