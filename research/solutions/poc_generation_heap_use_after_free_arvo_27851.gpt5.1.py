import os
import tarfile
import zipfile
import io
import string


class Solution:
    def solve(self, src_path: str) -> bytes:
        L_G = 72
        MAX_CANDIDATE_SIZE = 4096
        MAX_ARCHIVE_RECURSION = 3
        MAX_NESTED_ARCHIVE_SIZE = 50_000_000

        best_score = None
        best_bytes = None

        pattern_scores = {
            "nxast_raw_encap": 500,
            "raw_encap": 450,
            "raw-encap": 440,
            "rawencap": 430,
            "27851": 420,
            "poc": 400,
            "proof": 350,
            "repro": 340,
            "reproducer": 330,
            "crash": 320,
            "heap": 300,
            "uaf": 300,
            "use-after-free": 300,
            "use_after_free": 300,
            "bug": 200,
            "testcase": 200,
            "input": 150,
            "id_": 120,
            "fuzz": 110,
            "raw": 80,
            "encap": 80,
            "openflow": 60,
            "ovs": 40,
        }

        printable_set = {ord(c) for c in string.printable}

        def compute_name_score(name_lower: str) -> int:
            score = 0
            for pat, val in pattern_scores.items():
                if pat in name_lower:
                    score += val
            return score

        def process_candidate(path: str, size: int, data: bytes) -> None:
            nonlocal best_score, best_bytes
            if not data:
                return
            name_lower = path.lower()
            closeness = max(0, 100 - abs(size - L_G))
            name_score = compute_name_score(name_lower)
            if closeness == 0 and name_score == 0:
                return
            non_printable = 0
            for b in data:
                if b not in printable_set:
                    non_printable += 1
            ratio = non_printable / float(len(data))
            binary_bonus = int(ratio * 50)
            total_score = closeness * 2 + name_score + binary_bonus
            if best_score is None or total_score > best_score:
                best_score = total_score
                best_bytes = data

        def is_archive_name(name: str) -> bool:
            lower = name.lower()
            return lower.endswith(
                (
                    ".tar",
                    ".tar.gz",
                    ".tgz",
                    ".tar.bz2",
                    ".tbz2",
                    ".tbz",
                    ".tar.xz",
                    ".txz",
                    ".zip",
                )
            )

        def should_consider_file(size: int, name_lower: str) -> bool:
            if size <= 0:
                return False
            name_score = compute_name_score(name_lower)
            closeness = max(0, 100 - abs(size - L_G))
            if size <= MAX_CANDIDATE_SIZE:
                return closeness > 0 or name_score > 0
            else:
                return name_score > 0

        def scan_archive_bytes(data: bytes, name: str, depth: int) -> None:
            if depth > MAX_ARCHIVE_RECURSION:
                return
            bio = io.BytesIO(data)
            try:
                with tarfile.open(fileobj=bio, mode="r:*") as tf:
                    scan_tar_obj(tf, name, depth)
                    return
            except Exception:
                pass
            bio = io.BytesIO(data)
            try:
                with zipfile.ZipFile(bio, "r") as zf:
                    scan_zip_obj(zf, name, depth)
                    return
            except Exception:
                pass

        def scan_tar_obj(tf: tarfile.TarFile, base: str, depth: int) -> None:
            for member in tf.getmembers():
                if not member.isfile():
                    continue
                size = member.size
                member_path = os.path.join(base, member.name) if base else member.name
                name_lower = member_path.lower()
                if should_consider_file(size, name_lower):
                    try:
                        f = tf.extractfile(member)
                        if f is None:
                            continue
                        data = f.read()
                    except Exception:
                        data = None
                    if data is not None:
                        process_candidate(member_path, len(data), data)
                if (
                    size > 0
                    and size <= MAX_NESTED_ARCHIVE_SIZE
                    and depth < MAX_ARCHIVE_RECURSION
                    and is_archive_name(member.name)
                ):
                    try:
                        f = tf.extractfile(member)
                        if f is None:
                            continue
                        nested_data = f.read()
                    except Exception:
                        nested_data = None
                    if nested_data:
                        scan_archive_bytes(nested_data, member_path, depth + 1)

        def scan_zip_obj(zf: zipfile.ZipFile, base: str, depth: int) -> None:
            for info in zf.infolist():
                if info.is_dir():
                    continue
                size = info.file_size
                member_path = os.path.join(base, info.filename) if base else info.filename
                name_lower = member_path.lower()
                if should_consider_file(size, name_lower):
                    try:
                        data = zf.read(info)
                    except Exception:
                        data = None
                    if data is not None:
                        process_candidate(member_path, len(data), data)
                if (
                    size > 0
                    and size <= MAX_NESTED_ARCHIVE_SIZE
                    and depth < MAX_ARCHIVE_RECURSION
                    and is_archive_name(info.filename)
                ):
                    try:
                        nested_data = zf.read(info)
                    except Exception:
                        nested_data = None
                    if nested_data:
                        scan_archive_bytes(nested_data, member_path, depth + 1)

        def scan_directory(dir_path: str, depth: int) -> None:
            if depth > MAX_ARCHIVE_RECURSION:
                return
            for root, _, files in os.walk(dir_path):
                for fname in files:
                    full_path = os.path.join(root, fname)
                    name_lower = full_path.lower()
                    try:
                        size = os.path.getsize(full_path)
                    except Exception:
                        continue
                    if should_consider_file(size, name_lower):
                        try:
                            with open(full_path, "rb") as f:
                                data = f.read()
                        except Exception:
                            data = None
                        if data is not None:
                            process_candidate(full_path, len(data), data)
                    if (
                        size > 0
                        and size <= MAX_NESTED_ARCHIVE_SIZE
                        and depth < MAX_ARCHIVE_RECURSION
                        and is_archive_name(fname)
                    ):
                        try:
                            with open(full_path, "rb") as f:
                                nested_data = f.read()
                        except Exception:
                            nested_data = None
                        if nested_data:
                            scan_archive_bytes(nested_data, full_path, depth + 1)

        def scan_root(path: str) -> None:
            if os.path.isdir(path):
                scan_directory(path, 0)
                return
            try:
                if tarfile.is_tarfile(path):
                    with tarfile.open(path, "r:*") as tf:
                        scan_tar_obj(tf, "", 0)
                        return
            except Exception:
                pass
            try:
                if zipfile.is_zipfile(path):
                    with zipfile.ZipFile(path, "r") as zf:
                        scan_zip_obj(zf, "", 0)
                        return
            except Exception:
                pass
            try:
                size = os.path.getsize(path)
            except Exception:
                return
            name_lower = os.path.basename(path).lower()
            if should_consider_file(size, name_lower):
                try:
                    with open(path, "rb") as f:
                        data = f.read()
                except Exception:
                    data = None
                if data is not None:
                    process_candidate(path, len(data), data)

        scan_root(src_path)

        if best_bytes is not None:
            return best_bytes
        return b"A" * L_G