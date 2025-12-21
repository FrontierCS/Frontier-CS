import os
import tarfile
import tempfile
import re


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Try to analyze the source tarball to synthesize a PoC
        try:
            tmpdir = tempfile.mkdtemp(prefix="poc_gen_")
            try:
                with tarfile.open(src_path, "r:*") as tf:
                    def is_within_directory(directory: str, target: str) -> bool:
                        abs_directory = os.path.abspath(directory)
                        abs_target = os.path.abspath(target)
                        try:
                            common = os.path.commonpath([abs_directory, abs_target])
                        except ValueError:
                            return False
                        return common == abs_directory

                    for member in tf.getmembers():
                        member_path = os.path.join(tmpdir, member.name)
                        if not is_within_directory(tmpdir, member_path):
                            continue
                        try:
                            tf.extract(member, path=tmpdir)
                        except Exception:
                            continue
            except Exception:
                # If extraction fails, fall back to generic PoC
                return b"a=1;a/=0;"

            best_content = None
            best_score = None  # (priority, size)

            script_like_ext = {
                ".php", ".phpt", ".php3", ".php4", ".php5", ".phtml",
                ".rb", ".js", ".jsx", ".ts", ".tsx",
                ".py", ".pyw",
                ".lua", ".wren", ".nut",
                ".txt", ".src", ".code", ".script",
                ".conf", ".cfg", ".ini",
                ""
            }
            non_script_ext_bad = {
                ".c", ".h", ".cpp", ".cc", ".cxx", ".hpp", ".hh", ".ipp",
                ".java", ".go", ".cs", ".m", ".mm", ".swift", ".rs"
            }

            max_files = 2000
            files_processed = 0

            for root, dirs, files in os.walk(tmpdir):
                if files_processed >= max_files:
                    break
                for name in files:
                    if files_processed >= max_files:
                        break
                    path = os.path.join(root, name)
                    rel = os.path.relpath(path, tmpdir).lower()
                    parts = rel.replace("\\", "/").split("/")

                    # Basic priority heuristic
                    priority = 0
                    for part in parts:
                        if part in ("test", "tests", "testing"):
                            priority -= 2
                        elif part in ("example", "examples", "sample", "samples", "demo", "demos"):
                            priority -= 1

                    ext = os.path.splitext(name)[1].lower()
                    if ext in script_like_ext:
                        priority -= 1
                    if ext in non_script_ext_bad:
                        priority += 1

                    try:
                        size = os.path.getsize(path)
                    except OSError:
                        continue
                    if size <= 0 or size > 100 * 1024:
                        continue

                    try:
                        with open(path, "rb") as f:
                            raw = f.read(100000)
                    except OSError:
                        continue

                    if not raw:
                        continue

                    # Heuristic: mostly-text detection
                    text_chars = sum(1 for b in raw if 9 <= b <= 13 or 32 <= b <= 126)
                    if text_chars / float(len(raw)) < 0.85:
                        continue

                    try:
                        text = raw.decode("utf-8", errors="ignore")
                    except Exception:
                        continue

                    if "/=" not in text:
                        continue

                    files_processed += 1

                    score = (priority, size)
                    if best_score is None or score < best_score:
                        best_score = score
                        best_content = text

            if best_content:
                content = best_content
                new_content, n = re.subn(r"/=\s*[^;\n]*;", "/= 0;", content, count=1)
                if n == 0:
                    new_content, n = re.subn(r"/=\s*[^#\n]*", "/= 0", content, count=1)
                if n == 0:
                    content = content + "\na=1;a/=0;\n"
                    return content.encode("utf-8", errors="ignore")
                return new_content.encode("utf-8", errors="ignore")

        except Exception:
            pass

        # Fallback generic PoC: minimal compound division by zero
        return b"a=1;a/=0;"
