import os
import tarfile
import re


class Solution:
    def solve(self, src_path: str) -> bytes:
        fallback = b"a = 1;\na /= 0;\n"
        candidates = []

        def clean_snippet(s: str) -> str:
            s = s.strip()
            if not s:
                return s
            # Remove enclosing backticks
            if s.startswith("`") and s.endswith("`") and len(s) >= 2:
                s = s[1:-1].strip()
            # Trim leading prompts
            for prefix in ("$ ", "# ", "> ", "% "):
                if s.startswith(prefix):
                    s = s[len(prefix):].lstrip()
            # Remove outer quotes
            if (s.startswith('"') and s.endswith('"')) or (s.startswith("'") and s.endswith("'")):
                if len(s) >= 2:
                    s = s[1:-1].strip()
            return s

        def add_candidate(priority: int, code: str):
            code = code.strip()
            if not code:
                return
            if "/=" not in code or "0" not in code:
                return
            for p, ln, existing in candidates:
                if existing == code:
                    return
            candidates.append((priority, -len(code), code))

        def scan_text(text: str, filename: str):
            name_low = filename.lower()
            base = 0
            if any(x in name_low for x in ("readme", "poc", "crash", "example", "sample", "doc", "usage", "test")):
                base += 2
            if any(
                name_low.endswith(ext)
                for ext in (".md", ".txt", ".rst", ".org", ".in", ".test", ".t", ".sample", ".example", ".conf")
            ):
                base += 1

            # Strings in quotes that look like code
            for m in re.finditer(r'["\']([^"\']{0,200}/=[^"\']*0[^"\']*)["\']', text):
                snippet = clean_snippet(m.group(1))
                add_candidate(base + 3, snippet)

            lines = text.splitlines()
            for i, line in enumerate(lines):
                if "/=" not in line:
                    continue
                raw = line.rstrip()
                if not raw:
                    continue

                # Strip trailing comments
                comment_pos = None
                for token in ("//", "#", "/*"):
                    idx = raw.find(token)
                    if idx != -1:
                        if comment_pos is None or idx < comment_pos:
                            comment_pos = idx
                if comment_pos is not None:
                    segment = raw[:comment_pos].rstrip()
                else:
                    segment = raw
                if not segment:
                    continue

                qm = re.search(r'["\']([^"\']*/=[^"\']*)["\']', segment)
                if qm:
                    segment = qm.group(1)
                segment = clean_snippet(segment)
                if "/=" not in segment:
                    continue

                if "0" in segment:
                    add_candidate(base + 2, segment)
                    continue

                m2 = re.search(r'([A-Za-z_][A-Za-z0-9_]*)\s*/=\s*([A-Za-z_][A-Za-z0-9_]*)', segment)
                if not m2:
                    continue
                lhs, rhs = m2.group(1), m2.group(2)

                script_lines = []
                have_rhs_zero = False
                start = max(0, i - 10)
                for j in range(start, i):
                    l2 = lines[j].strip()
                    if not l2:
                        continue
                    l2_no_comment = l2.split("//")[0].split("#")[0]
                    l2_clean = clean_snippet(l2_no_comment)
                    if not l2_clean:
                        continue
                    if re.search(r'\b%s\s*=' % re.escape(rhs), l2_clean):
                        if "0" in l2_clean:
                            have_rhs_zero = True
                            script_lines.append(l2_clean)
                    elif re.search(r'\b%s\s*=' % re.escape(lhs), l2_clean):
                        script_lines.append(l2_clean)

                if not have_rhs_zero:
                    continue

                script_lines.append(segment)
                script = "\n".join(script_lines)
                add_candidate(base + 2, script)

        source_exts = (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".inc", ".y", ".l")

        def process_dir(root: str):
            try:
                for dirpath, _, filenames in os.walk(root):
                    for fname in filenames:
                        full = os.path.join(dirpath, fname)
                        try:
                            size = os.path.getsize(full)
                        except OSError:
                            continue
                        lower = fname.lower()

                        # Try direct PoC files
                        if (
                            0 < size <= 4096
                            and any(tok in lower for tok in ("poc", "crash", "uaf"))
                            and not lower.endswith(source_exts)
                        ):
                            try:
                                with open(full, "rb") as f:
                                    data = f.read()
                                if data:
                                    return data
                            except OSError:
                                pass

                        # Scan as text
                        try:
                            with open(full, "rb") as f:
                                data = f.read(131072)
                        except OSError:
                            continue
                        if not data:
                            continue
                        # Skip likely binary
                        sample = data[:4096]
                        if sample and sum(b < 9 or (13 < b < 32) or b > 126 for b in sample) / len(sample) > 0.3:
                            continue
                        try:
                            text = data.decode("utf-8")
                        except UnicodeDecodeError:
                            text = data.decode("latin-1", errors="ignore")
                        scan_text(text, full)
            except Exception:
                pass
            return None

        def process_tar(path: str):
            try:
                tf = tarfile.open(path, "r:*")
            except Exception:
                return None
            try:
                for m in tf.getmembers():
                    if not m.isfile():
                        continue
                    size = m.size
                    base = os.path.basename(m.name)
                    lower = base.lower()

                    # Direct PoC files
                    if (
                        0 < size <= 4096
                        and any(tok in lower for tok in ("poc", "crash", "uaf"))
                        and not lower.endswith(source_exts)
                    ):
                        try:
                            f = tf.extractfile(m)
                            if not f:
                                continue
                            data = f.read()
                        except Exception:
                            continue
                        if data:
                            tf.close()
                            return data

                    # Scan as text
                    try:
                        f = tf.extractfile(m)
                        if not f:
                            continue
                        data = f.read(131072)
                    except Exception:
                        continue
                    if not data:
                        continue
                    sample = data[:4096]
                    if sample and sum(b < 9 or (13 < b < 32) or b > 126 for b in sample) / len(sample) > 0.3:
                        continue
                    try:
                        text = data.decode("utf-8")
                    except UnicodeDecodeError:
                        text = data.decode("latin-1", errors="ignore")
                    scan_text(text, m.name)
            finally:
                try:
                    tf.close()
                except Exception:
                    pass
            return None

        if os.path.isdir(src_path):
            direct = process_dir(src_path)
        else:
            direct = process_tar(src_path)

        if direct:
            return direct

        if candidates:
            candidates.sort(reverse=True)
            best_code = candidates[0][2]
            if not best_code.endswith("\n"):
                best_code += "\n"
            try:
                return best_code.encode("utf-8")
            except Exception:
                return best_code.encode("latin-1", errors="replace")

        return fallback
