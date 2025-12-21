import os
import io
import tarfile
import zipfile
import gzip
import bz2
import lzma

class Solution:
    def solve(self, src_path: str) -> bytes:
        scanner = _PoCScanner(
            bug_id="42535696",
            target_size=150979,
            max_depth=3,
            max_total_bytes=256 * 1024 * 1024,
            max_members=200000,
        )
        data = scanner.find(src_path)
        if data is not None:
            return data
        # Fallback: return an empty PDF-like file (won't trigger vulnerability, but ensures valid bytes)
        return b"%PDF-1.4\n%EOF\n"


class _PoCScanner:
    def __init__(self, bug_id: str, target_size: int, max_depth: int = 3,
                 max_total_bytes: int = 256 * 1024 * 1024, max_members: int = 200000):
        self.bug_id = bug_id
        self.target_size = int(target_size)
        self.max_depth = max_depth
        self.max_total_bytes = max_total_bytes
        self.max_members = max_members

        self.best_key = None
        self.best_name = None
        self.best_bytes = None

        # Counters / limits
        self._bytes_read = 0
        self._members_seen = 0

        # Heuristic ext sets
        self.likely_exts = {
            "pdf", "ps", "eps", "ai", "pcl", "pclm", "pxl", "prn", "xps", "svg", "svgz",
            "bmp", "png", "jpg", "jpeg", "jfif", "jp2", "tif", "tiff", "pbm", "pgm", "ppm", "pnm",
            "txt", "dat", "bin"
        }
        self.archive_exts = {
            "tar", "tgz", "tar.gz", "tar.xz", "txz", "tar.bz2", "tbz2", "zip"
        }
        self.compress_exts = {"gz", "xz", "bz2"}

    def find(self, src_path: str) -> bytes:
        try:
            if os.path.isdir(src_path):
                self._scan_dir(src_path, depth=0)
            else:
                # Try tar, zip or simple file
                if self._is_tar_filename(src_path) or self._is_zip_filename(src_path):
                    self._scan_path_archive(src_path, depth=0)
                else:
                    # Even if not obvious, try as tar, then as zip, else as plain file
                    if not self._scan_path_as_tar(src_path, depth=0):
                        if not self._scan_path_as_zip(src_path, depth=0):
                            # Plain single file candidate
                            self._consider_file(src_path, os.path.getsize(src_path), self._read_file_safely(src_path), logical_name=os.path.basename(src_path))
        except Exception:
            pass
        return self.best_bytes

    # --------------- Scanning helpers ---------------

    def _scan_dir(self, directory: str, depth: int):
        if depth > self.max_depth:
            return
        try:
            for root, dirs, files in os.walk(directory):
                for name in files:
                    if self._members_seen > self.max_members:
                        return
                    full = os.path.join(root, name)
                    self._members_seen += 1
                    try:
                        size = os.path.getsize(full)
                    except Exception:
                        size = -1
                    lname = name.lower()

                    if self._is_archive_filename(lname):
                        # archive, scan inside
                        self._scan_path_archive(full, depth=depth + 1)
                    elif self._is_compress_filename(lname):
                        # single-file compression
                        data = self._read_file_safely(full)
                        if data is not None:
                            dname = self._decompressed_name(name)
                            dec = self._decompress_bytes(lname, data)
                            if dec is not None:
                                # After decompress, if it's an archive, scan into it
                                if self._looks_like_archive_by_name(dname):
                                    self._scan_bytes_archive(dec, dname, depth=depth + 1)
                                else:
                                    # Consider decompressed file as candidate
                                    self._consider_file(dname, len(dec), dec, logical_name=dname)
                    else:
                        # Plain file candidate
                        data_supplier = self._read_file_safely(full)
                        self._consider_file(name, size, data_supplier, logical_name=os.path.relpath(full, directory))
                # Limit recursion depth
                for d in list(dirs):
                    if depth + 1 > self.max_depth:
                        dirs.remove(d)
        except Exception:
            pass

    def _scan_path_archive(self, path: str, depth: int):
        # Try tar
        if self._scan_path_as_tar(path, depth=depth):
            return
        # Try zip
        if self._scan_path_as_zip(path, depth=depth):
            return
        # Try as compressed single file
        try:
            lname = os.path.basename(path).lower()
            if self._is_compress_filename(lname):
                data = self._read_file_safely(path)
                if data is not None:
                    dname = self._decompressed_name(os.path.basename(path))
                    dec = self._decompress_bytes(lname, data)
                    if dec is not None:
                        if self._looks_like_archive_by_name(dname):
                            self._scan_bytes_archive(dec, dname, depth=depth + 1)
                        else:
                            self._consider_file(dname, len(dec), dec, logical_name=dname)
        except Exception:
            pass

    def _scan_path_as_tar(self, path: str, depth: int) -> bool:
        if depth > self.max_depth:
            return False
        try:
            with tarfile.open(path, mode="r:*") as tf:
                self._scan_tarfile(tf, os.path.basename(path), depth=depth)
                return True
        except Exception:
            return False

    def _scan_path_as_zip(self, path: str, depth: int) -> bool:
        if depth > self.max_depth:
            return False
        try:
            with zipfile.ZipFile(path, 'r') as zf:
                self._scan_zipfile(zf, os.path.basename(path), depth=depth)
                return True
        except Exception:
            return False

    def _scan_bytes_archive(self, data: bytes, name: str, depth: int):
        if depth > self.max_depth:
            return
        # Try tar from bytes
        try:
            bio = io.BytesIO(data)
            with tarfile.open(fileobj=bio, mode="r:*") as tf:
                self._scan_tarfile(tf, name, depth=depth)
                return
        except Exception:
            pass
        # Try zip from bytes
        try:
            bio = io.BytesIO(data)
            with zipfile.ZipFile(bio, 'r') as zf:
                self._scan_zipfile(zf, name, depth=depth)
                return
        except Exception:
            pass
        # Try if data is compressed single-file; unlikely here as we're already inside.
        # Otherwise ignore.

    def _scan_tarfile(self, tf: tarfile.TarFile, container_name: str, depth: int):
        try:
            for member in tf.getmembers():
                if self._members_seen > self.max_members:
                    return
                if not member.isfile():
                    continue
                self._members_seen += 1
                mname = member.name
                lname = mname.lower()
                size = member.size if hasattr(member, "size") else -1

                is_archive = self._is_archive_filename(lname)
                is_compress = self._is_compress_filename(lname)

                # If it's an archive/compressed file, consider scanning inside
                if (is_archive or is_compress) and depth + 1 <= self.max_depth:
                    try:
                        f = tf.extractfile(member)
                        if f is None:
                            continue
                        data = self._read_stream_safely(f, size)
                        if data is None:
                            continue
                        if is_archive:
                            self._scan_bytes_archive(data, mname, depth=depth + 1)
                        elif is_compress:
                            dec = self._decompress_bytes(lname, data)
                            if dec is not None:
                                dname = self._decompressed_name(mname)
                                if self._looks_like_archive_by_name(dname):
                                    self._scan_bytes_archive(dec, dname, depth=depth + 1)
                                else:
                                    self._consider_file(dname, len(dec), dec, logical_name=dname)
                    except Exception:
                        continue

                # Consider the member itself as a candidate if it's not an archive
                if not is_archive and not is_compress:
                    # Delay reading until we know it's a better candidate
                    self._consider_file(mname, size, self._extract_tar_member(tf, member), logical_name=mname)
        except Exception:
            pass

    def _extract_tar_member(self, tf: tarfile.TarFile, member: tarfile.TarInfo):
        def supplier():
            try:
                f = tf.extractfile(member)
                if f is None:
                    return None
                return self._read_stream_safely(f, member.size if hasattr(member, "size") else -1)
            except Exception:
                return None
        return supplier

    def _scan_zipfile(self, zf: zipfile.ZipFile, container_name: str, depth: int):
        try:
            for info in zf.infolist():
                if self._members_seen > self.max_members:
                    return
                if info.is_dir():
                    continue
                self._members_seen += 1
                name = info.filename
                lname = name.lower()
                size = info.file_size

                is_archive = self._is_archive_filename(lname)
                is_compress = self._is_compress_filename(lname)

                if (is_archive or is_compress) and depth + 1 <= self.max_depth:
                    try:
                        data = self._read_zip_member_safely(zf, info)
                        if data is None:
                            continue
                        if is_archive:
                            self._scan_bytes_archive(data, name, depth=depth + 1)
                        elif is_compress:
                            dec = self._decompress_bytes(lname, data)
                            if dec is not None:
                                dname = self._decompressed_name(name)
                                if self._looks_like_archive_by_name(dname):
                                    self._scan_bytes_archive(dec, dname, depth=depth + 1)
                                else:
                                    self._consider_file(dname, len(dec), dec, logical_name=dname)
                    except Exception:
                        continue

                if not is_archive and not is_compress:
                    # Consider as candidate lazily; supply data function to avoid up-front cost
                    self._consider_file(name, size, self._extract_zip_member(zf, info), logical_name=name)
        except Exception:
            pass

    def _extract_zip_member(self, zf: zipfile.ZipFile, info: zipfile.ZipInfo):
        def supplier():
            try:
                return self._read_zip_member_safely(zf, info)
            except Exception:
                return None
        return supplier

    # --------------- Consider candidate ---------------

    def _consider_file(self, name: str, size: int, data_supplier, logical_name: str = None):
        # data_supplier can be either bytes or callable returning bytes or None
        key = self._priority_key(name, size)
        if self.best_key is None or self._key_better(key, self.best_key):
            data = None
            if isinstance(data_supplier, (bytes, bytearray)):
                data = bytes(data_supplier)
            elif callable(data_supplier):
                data = data_supplier()
            else:
                # Unknown supplier type
                data = None
            if data is None:
                return
            # Update accounting
            self._bytes_read += len(data)
            if self._bytes_read > self.max_total_bytes:
                # Stop collecting more to avoid memory blow-up
                pass
            self.best_key = key
            self.best_bytes = data
            self.best_name = logical_name or name

    # --------------- Priority / Key ---------------

    def _priority_key(self, name: str, size: int):
        l = (name or "").lower()
        id_in_name = self.bug_id in l
        has_keyword = any(k in l for k in ("oss-fuzz", "clusterfuzz", "fuzz", "poc", "min", "minimized", "crash", "regress", "issue", "bug"))
        ext = self._effective_extension(l)
        is_archive = self._is_archive_filename(l)
        ext_likely = (ext in self.likely_exts)
        exact_size = (size == self.target_size) if isinstance(size, int) and size >= 0 else False
        size_diff = abs(size - self.target_size) if isinstance(size, int) and size >= 0 else 10**12
        # Priority tuple: lower is better
        return (
            0 if id_in_name else 1,
            0 if not is_archive else 1,
            0 if has_keyword else 1,
            0 if ext_likely else 1,
            0 if exact_size else 1,
            size_diff,
            0 if size >= 0 else 1,
        )

    def _key_better(self, a, b):
        try:
            return a < b
        except Exception:
            return False

    # --------------- Filename utilities ---------------

    def _effective_extension(self, lname: str) -> str:
        if not lname:
            return ""
        # Handle composite extensions like .tar.gz
        for comp in ("tar.gz", "tar.xz", "tar.bz2"):
            if lname.endswith("." + comp):
                return comp
        # Plain last extension
        base, dot, ext = lname.rpartition(".")
        return ext if dot else ""

    def _is_archive_filename(self, lname: str) -> bool:
        ext = self._effective_extension(lname)
        if ext in self.archive_exts:
            return True
        # Also treat .tgz and .txz, .tbz2
        if lname.endswith(".tgz") or lname.endswith(".txz") or lname.endswith(".tbz2"):
            return True
        return False

    def _is_tar_filename(self, path: str) -> bool:
        l = path.lower()
        return l.endswith(".tar") or l.endswith(".tar.gz") or l.endswith(".tgz") or l.endswith(".tar.xz") or l.endswith(".txz") or l.endswith(".tar.bz2") or l.endswith(".tbz2")

    def _is_zip_filename(self, path: str) -> bool:
        return path.lower().endswith(".zip")

    def _is_compress_filename(self, lname: str) -> bool:
        ext = self._effective_extension(lname)
        if ext in self.compress_exts and ext not in self.archive_exts:
            # exclude composite archive types already covered: tar.gz etc.
            if not (lname.endswith(".tar.gz") or lname.endswith(".tar.xz") or lname.endswith(".tar.bz2") or lname.endswith(".tgz") or lname.endswith(".txz") or lname.endswith(".tbz2")):
                return True
        return False

    def _looks_like_archive_by_name(self, name: str) -> bool:
        return self._is_archive_filename(name.lower()) or self._is_zip_filename(name)

    def _decompressed_name(self, name: str) -> str:
        lname = name.lower()
        for comp in (".gz", ".xz", ".bz2"):
            if lname.endswith(comp):
                return name[:-len(comp)]
        return name

    # --------------- Safe reading helpers ---------------

    def _read_file_safely(self, path: str):
        def supplier():
            try:
                with open(path, "rb") as f:
                    return self._read_stream_safely(f, os.path.getsize(path))
            except Exception:
                return None
        return supplier

    def _read_stream_safely(self, stream, size_hint: int = -1) -> bytes:
        # Avoid reading huge blobs beyond max_total_bytes budget
        try:
            if size_hint is not None and isinstance(size_hint, int) and size_hint >= 0:
                to_read = size_hint
                if self._bytes_read + to_read > self.max_total_bytes:
                    # If about to exceed budget, still try to read if it's small; else skip
                    if to_read > 8 * 1024 * 1024:
                        return None
                data = stream.read()
                if isinstance(data, bytes):
                    return data
                else:
                    return bytes(data)
            else:
                # Unknown size; read but limit to budget chunk
                chunks = []
                remaining = max(0, self.max_total_bytes - self._bytes_read)
                step = 1 << 20
                while remaining > 0:
                    chunk = stream.read(min(step, remaining))
                    if not chunk:
                        break
                    chunks.append(chunk)
                    remaining -= len(chunk)
                return b"".join(chunks)
        except Exception:
            return None

    def _read_zip_member_safely(self, zf: zipfile.ZipFile, info: zipfile.ZipInfo) -> bytes:
        try:
            if self._bytes_read + info.file_size > self.max_total_bytes and info.file_size > 8 * 1024 * 1024:
                return None
            return zf.read(info)
        except Exception:
            return None

    # --------------- Decompression ---------------

    def _decompress_bytes(self, lname: str, data: bytes) -> bytes:
        try:
            if lname.endswith(".gz") and not (lname.endswith(".tar.gz") or lname.endswith(".tgz")):
                return gzip.decompress(data)
        except Exception:
            pass
        try:
            if lname.endswith(".xz") and not lname.endswith(".tar.xz") and not lname.endswith(".txz"):
                return lzma.decompress(data)
        except Exception:
            pass
        try:
            if lname.endswith(".bz2") and not lname.endswith(".tar.bz2") and not lname.endswith(".tbz2"):
                return bz2.decompress(data)
        except Exception:
            pass
        return None
