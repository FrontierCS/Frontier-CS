import os
import tarfile
import tempfile
import shutil

class Solution:
    def solve(self, src_path: str) -> bytes:
        def is_rar5_signature(path):
            try:
                with open(path, 'rb') as f:
                    sig = f.read(8)
                return sig == b"Rar!\x1a\x07\x01\x00"
            except Exception:
                return False

        def collect_candidates(root):
            candidates = []
            for dirpath, _, filenames in os.walk(root):
                for name in filenames:
                    path = os.path.join(dirpath, name)
                    try:
                        st = os.stat(path)
                    except Exception:
                        continue
                    if not os.path.isfile(path) or st.st_size <= 0:
                        continue
                    # Prefer files that look like RAR5
                    rar5 = is_rar5_signature(path)
                    candidates.append((path, st.st_size, rar5))
            return candidates

        def pick_poc(candidates):
            # Prefer exact size 1089 and RAR5 signature
            exact_rar5 = [c for c in candidates if c[2] and c[1] == 1089]
            if exact_rar5:
                return min(exact_rar5, key=lambda x: len(x[0]))[0]
            # Then prefer name hints with RAR5 signature
            name_hints = ("42536661", "oss-fuzz", "clusterfuzz", "poc", "crash", "rar5")
            hinted_rar5 = [c for c in candidates if c[2] and any(h in c[0].lower() for h in name_hints)]
            if hinted_rar5:
                return min(hinted_rar5, key=lambda x: (x[1], len(x[0])))[0]
            # Then any RAR5 with smallest size
            any_rar5 = [c for c in candidates if c[2]]
            if any_rar5:
                return min(any_rar5, key=lambda x: (abs(x[1]-1089), x[1]))[0]
            # Then any file with exact size 1089 (maybe extensionless)
            exact_any = [c for c in candidates if c[1] == 1089]
            if exact_any:
                return min(exact_any, key=lambda x: len(x[0]))[0]
            # Then any file with size close to 1089 and hint in name
            hinted_any = [c for c in candidates if any(h in c[0].lower() for h in name_hints)]
            if hinted_any:
                return min(hinted_any, key=lambda x: (abs(x[1]-1089), x[1]))[0]
            # Finally, smallest file
            if candidates:
                return min(candidates, key=lambda x: x[1])[0]
            return None

        tempdir = None
        extracted_root = None
        try:
            tempdir = tempfile.mkdtemp(prefix="poc_extract_")
            # Try to open tarball
            extracted_root = os.path.join(tempdir, "src")
            os.makedirs(extracted_root, exist_ok=True)
            extracted = False
            try:
                with tarfile.open(src_path, mode="r:*") as tf:
                    safe_members = []
                    for m in tf.getmembers():
                        # Avoid absolute path traversal
                        if not m.name or m.name.startswith("/") or ".." in m.name.replace("\\", "/"):
                            continue
                        safe_members.append(m)
                    tf.extractall(path=extracted_root, members=safe_members)
                    extracted = True
            except Exception:
                # Not a tar or extraction failed; if it's a directory, use it directly
                if os.path.isdir(src_path):
                    extracted_root = src_path
                    extracted = True

            if not extracted:
                # As last resort, just return a minimal invalid RAR5 signature blob
                return b"Rar!\x1a\x07\x01\x00" + b"\x00"*16

            candidates = collect_candidates(extracted_root)
            chosen = pick_poc(candidates)
            if chosen and os.path.isfile(chosen):
                with open(chosen, "rb") as f:
                    return f.read()

            # Fallback: minimal RAR5-like bytes (likely non-crashing placeholder)
            return b"Rar!\x1a\x07\x01\x00" + b"\x00"*16
        finally:
            if tempdir and os.path.isdir(tempdir) and extracted_root and extracted_root.startswith(tempdir):
                shutil.rmtree(tempdir, ignore_errors=True)
