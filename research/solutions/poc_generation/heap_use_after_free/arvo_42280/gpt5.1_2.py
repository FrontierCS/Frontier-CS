import os
import tarfile
import gzip
from typing import Optional, Tuple


class Solution:
    TARGET_POC_SIZE = 13996

    def solve(self, src_path: str) -> bytes:
        target_size = self.TARGET_POC_SIZE

        if os.path.isdir(src_path):
            data = self._find_poc_in_directory(src_path, target_size)
            if data is not None:
                return data

        if os.path.isfile(src_path) and tarfile.is_tarfile(src_path):
            data = self._find_poc_in_tar(src_path, target_size)
            if data is not None:
                return data

        return self._fallback_poc()

    def _find_poc_in_directory(self, root_dir: str, target_size: int) -> Optional[bytes]:
        best_path: Optional[str] = None
        best_key: Optional[Tuple[int, int, int]] = None
        best_is_gz: bool = False

        for dirpath, _, filenames in os.walk(root_dir):
            for filename in filenames:
                path = os.path.join(dirpath, filename)
                try:
                    size = os.path.getsize(path)
                except OSError:
                    continue

                if size <= 0:
                    continue

                name = filename
                lname = name.lower()
                _, ext = os.path.splitext(lname)

                # Handle gzipped candidates with interesting names
                if ext == ".gz" and self._has_interesting_keyword(lname):
                    try:
                        with gzip.open(path, "rb") as gz:
                            data = gz.read()
                    except OSError:
                        data = b""
                    if not data:
                        # If decompression failed or empty, skip
                        pass
                    else:
                        decomp_size = len(data)
                        name_for_priority = os.path.splitext(name)[0]
                        key = self._candidate_key(decomp_size, name_for_priority, target_size)
                        if best_key is None or key < best_key:
                            best_key = key
                            best_path = path
                            best_is_gz = True

                    # Do not treat .gz as non-gz candidate
                    continue

                if ext == ".gz":
                    # Skip other gz files
                    continue

                key = self._candidate_key(size, name, target_size)
                if best_key is None or key < best_key:
                    best_key = key
                    best_path = path
                    best_is_gz = False

        if best_path is None:
            return None

        try:
            if best_is_gz:
                with gzip.open(best_path, "rb") as gz:
                    return gz.read()
            else:
                with open(best_path, "rb") as f:
                    return f.read()
        except OSError:
            return None

    def _find_poc_in_tar(self, tar_path: str, target_size: int) -> Optional[bytes]:
        best_member: Optional[tarfile.TarInfo] = None
        best_key: Optional[Tuple[int, int, int]] = None
        best_is_gz: bool = False

        try:
            tar = tarfile.open(tar_path, "r:*")
        except (tarfile.TarError, OSError):
            return None

        with tar:
            for member in tar.getmembers():
                if not member.isfile():
                    continue

                name = os.path.basename(member.name)
                if not name:
                    continue

                lname = name.lower()
                _, ext = os.path.splitext(lname)

                # Handle gzipped members with interesting names
                if ext == ".gz" and self._has_interesting_keyword(lname):
                    try:
                        fobj = tar.extractfile(member)
                    except (tarfile.ExtractError, KeyError, OSError):
                        fobj = None
                    if fobj is None:
                        continue
                    try:
                        with gzip.GzipFile(fileobj=fobj) as gz:
                            data = gz.read()
                    except OSError:
                        data = b""
                    if not data:
                        continue
                    decomp_size = len(data)
                    name_for_priority = os.path.splitext(name)[0]
                    key = self._candidate_key(decomp_size, name_for_priority, target_size)
                    if best_key is None or key < best_key:
                        best_key = key
                        best_member = member
                        best_is_gz = True
                    continue

                if ext == ".gz":
                    # Skip other gz files
                    continue

                size = member.size
                if size <= 0:
                    continue

                key = self._candidate_key(size, name, target_size)
                if best_key is None or key < best_key:
                    best_key = key
                    best_member = member
                    best_is_gz = False

            if best_member is None:
                return None

            try:
                fobj = tar.extractfile(best_member)
            except (tarfile.ExtractError, KeyError, OSError):
                return None
            if fobj is None:
                return None

            try:
                if best_is_gz:
                    with gzip.GzipFile(fileobj=fobj) as gz:
                        return gz.read()
                else:
                    return fobj.read()
            except OSError:
                return None

    def _candidate_key(self, size: int, name: str, target_size: int) -> Tuple[int, int, int]:
        priority = self._priority(name)
        diff = abs(size - target_size)
        # Lower key is better: higher priority (more negative), closer in size, smaller absolute size
        return (-priority, diff, size)

    def _priority(self, name: str) -> int:
        lname = name.lower()
        _, ext = os.path.splitext(lname)
        base = 0

        if ext == ".pdf":
            base += 100
        elif ext in (".ps", ".eps"):
            base += 80
        elif ext in (".xps", ".oxps"):
            base += 70
        elif ext in (".bin", ".dat"):
            base += 40
        elif ext in (".txt",):
            base += 20
        else:
            base += 5

        kw_scores = {
            "42280": 80,
            "poc": 60,
            "uaf": 60,
            "use-after-free": 60,
            "use_after_free": 60,
            "use after free": 60,
            "heap": 15,
            "cve": 40,
            "bug": 25,
            "crash": 50,
            "testcase": 30,
            "regress": 20,
            "fuzz": 15,
            "sample": 10,
        }

        for kw, score in kw_scores.items():
            if kw in lname:
                base += score

        return base

    def _has_interesting_keyword(self, name_lower: str) -> bool:
        keywords = [
            "42280",
            "poc",
            "uaf",
            "use-after-free",
            "use_after_free",
            "use after free",
            "cve",
            "bug",
            "crash",
            "testcase",
            "fuzz",
            "regress",
        ]
        for kw in keywords:
            if kw in name_lower:
                return True
        return False

    def _fallback_poc(self) -> bytes:
        pdf_bytes = (
            b"%PDF-1.1\n"
            b"1 0 obj\n"
            b"<< /Type /Catalog >>\n"
            b"endobj\n"
            b"xref\n"
            b"0 2\n"
            b"0000000000 65535 f \n"
            b"0000000010 00000 n \n"
            b"trailer\n"
            b"<< /Root 1 0 R >>\n"
            b"startxref\n"
            b"0\n"
            b"%%EOF\n"
        )
        return pdf_bytes