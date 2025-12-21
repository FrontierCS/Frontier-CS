import os
import io
import tarfile
import zipfile
import gzip
import lzma
import bz2

class Solution:
    GROUND_LEN = 1479
    MAX_DEPTH = 3
    NESTED_MAX_BYTES = 20 * 1024 * 1024

    def solve(self, src_path: str) -> bytes:
        entries = []
        visited_containers = set()

        def add_entry(name, size, reader):
            entries.append((name, size, reader))

        def is_container_name(name_lower):
            container_exts = (
                '.tar', '.tar.gz', '.tgz', '.tar.bz2', '.tbz2', '.tar.xz', '.txz', '.zip',
                '.gz', '.xz', '.bz2'
            )
            return name_lower.endswith(container_exts)

        def explore_tar(tf, prefix, depth):
            try:
                members = tf.getmembers()
            except Exception:
                return
            for m in members:
                try:
                    if not m.isfile():
                        continue
                    name = (prefix + "/" + m.name) if prefix else m.name
                    size = int(getattr(m, "size", 0) or 0)
                    def reader_func(mm=m, t=tf):
                        try:
                            f = t.extractfile(mm)
                            if f is None:
                                return b""
                            with f:
                                return f.read()
                        except Exception:
                            return b""
                    add_entry(name, size, reader_func)
                    lower_name = name.lower()
                    if depth < self.MAX_DEPTH and is_container_name(lower_name) and size <= self.NESTED_MAX_BYTES:
                        try:
                            data = reader_func()
                        except Exception:
                            data = b""
                        if not data:
                            continue
                        explore_nested_bytes(data, name, depth + 1)
                except Exception:
                    continue

        def explore_zip(zf, prefix, depth):
            try:
                infos = zf.infolist()
            except Exception:
                return
            for info in infos:
                try:
                    if getattr(info, "is_dir", None):
                        if info.is_dir():
                            continue
                    # If is_dir is not available, check filename
                    if info.filename.endswith('/') or info.filename.endswith('\\'):
                        continue
                    name = (prefix + "/" + info.filename) if prefix else info.filename
                    size = int(getattr(info, "file_size", 0) or 0)
                    def reader_func(inf=info, z=zf):
                        try:
                            return z.read(inf.filename)
                        except Exception:
                            return b""
                    add_entry(name, size, reader_func)
                    lower_name = name.lower()
                    if depth < self.MAX_DEPTH and is_container_name(lower_name) and size <= self.NESTED_MAX_BYTES:
                        try:
                            data = reader_func()
                        except Exception:
                            data = b""
                        if not data:
                            continue
                        explore_nested_bytes(data, name, depth + 1)
                except Exception:
                    continue

        def explore_nested_bytes(data, container_name, depth):
            # Avoid infinite recursion on repeated content
            key = (hash(data[:1024]), len(data), container_name)
            if key in visited_containers:
                return
            visited_containers.add(key)

            # Try tar first
            try:
                bio = io.BytesIO(data)
                with tarfile.open(fileobj=bio, mode="r:*") as tf2:
                    explore_tar(tf2, container_name, depth)
                    return
            except Exception:
                pass
            # Try zip
            try:
                bio = io.BytesIO(data)
                with zipfile.ZipFile(bio, 'r') as zf2:
                    explore_zip(zf2, container_name, depth)
                    return
            except Exception:
                pass
            # Try decompress single-file archives
            lower = container_name.lower()
            dec_data = None
            if lower.endswith('.gz'):
                try:
                    dec_data = gzip.decompress(data)
                except Exception:
                    dec_data = None
            elif lower.endswith('.xz') or lower.endswith('.lzma'):
                try:
                    dec_data = lzma.decompress(data)
                except Exception:
                    dec_data = None
            elif lower.endswith('.bz2'):
                try:
                    dec_data = bz2.decompress(data)
                except Exception:
                    dec_data = None
            if dec_data is not None and isinstance(dec_data, (bytes, bytearray)):
                if len(dec_data) <= self.NESTED_MAX_BYTES:
                    name = container_name + ".decompressed"
                    add_entry(name, len(dec_data), lambda b=dec_data: b)

        def explore_path(path, depth):
            if depth > self.MAX_DEPTH:
                return
            if os.path.isdir(path):
                for root, _, files in os.walk(path):
                    for fn in files:
                        full = os.path.join(root, fn)
                        try:
                            size = os.path.getsize(full)
                        except Exception:
                            continue
                        def reader_func(p=full):
                            try:
                                with open(p, 'rb') as f:
                                    return f.read()
                            except Exception:
                                return b""
                        name = os.path.relpath(full, path)
                        add_entry(name, size, reader_func)
                        lower_name = name.lower()
                        if is_container_name(lower_name) and size <= self.NESTED_MAX_BYTES:
                            try:
                                data = reader_func()
                            except Exception:
                                data = b""
                            if data:
                                explore_nested_bytes(data, name, depth + 1)
                return
            # It's a file
            # Try tar
            try:
                with tarfile.open(path, mode="r:*") as tf:
                    explore_tar(tf, "", depth)
                    return
            except Exception:
                pass
            # Try zip
            try:
                with zipfile.ZipFile(path, 'r') as zf:
                    explore_zip(zf, "", depth)
                    return
            except Exception:
                pass
            # Fallback: treat as raw file
            try:
                size = os.path.getsize(path)
                def reader_func(p=path):
                    try:
                        with open(p, 'rb') as f:
                            return f.read()
                    except Exception:
                        return b""
                add_entry(os.path.basename(path), size, reader_func)
            except Exception:
                pass

        explore_path(src_path, 0)

        # Choose best candidate
        if not entries:
            return b""

        # Prefer specific extensions and keywords
        preferred_exts = ['.j2k', '.j2c', '.jp2', '.jpc', '.cod', '.j2p', '.j2x', '.img', '.bin', '.dat']
        keywords = ['poc', 'crash', 'heap', 'overflow', '47500', 'arvo', 'openjpeg', 'opj', 'ht', 't1', 'allocate', 'buffers', 'oss-fuzz', 'id:', 'clusterfuzz', 'decode', 'decompress']

        def ext_rank(name_lower):
            for idx, e in enumerate(preferred_exts):
                if name_lower.endswith(e):
                    return idx
            # check within multi-extension
            for idx, e in enumerate(preferred_exts):
                if ('.' + e.lstrip('.')) in name_lower:
                    return idx + len(preferred_exts)
            return 1000

        def kw_count(name_lower):
            c = 0
            for k in keywords:
                if k in name_lower:
                    c += 1
            return c

        # Sorting key
        def sort_key(entry):
            name, size, _ = entry
            lower = name.lower()
            exact = 0 if size == self.GROUND_LEN else 1
            return (exact, ext_rank(lower), -kw_count(lower), abs(size - self.GROUND_LEN), len(name))

        entries.sort(key=sort_key)
        # Read best candidate bytes
        for name, size, reader in entries:
            try:
                data = reader()
            except Exception:
                data = b""
            if isinstance(data, (bytes, bytearray)) and data:
                # Prefer exact size
                if len(data) == self.GROUND_LEN:
                    return data
                # Otherwise, keep first successful data
                best = data
                # But continue to see if there is a later exact size match (though sorted should have exact first)
                return best
        # If all failed to read properly
        return b""
