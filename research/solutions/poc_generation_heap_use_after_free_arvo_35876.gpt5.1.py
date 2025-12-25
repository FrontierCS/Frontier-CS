import os
import tarfile
import tempfile
import subprocess
import stat
import re
import shutil


def _extract_tarball(src_path: str) -> str:
    tmp_dir = tempfile.mkdtemp(prefix="poc_gen_")
    try:
        with tarfile.open(src_path, "r:*") as tf:
            tf.extractall(tmp_dir)
    except Exception:
        # If extraction fails for some reason, still return the dir (may be empty)
        pass
    return tmp_dir


def _find_elf_binaries(root: str):
    elf_bins = []
    for dirpath, dirnames, filenames in os.walk(root):
        for fname in filenames:
            path = os.path.join(dirpath, fname)
            try:
                st = os.stat(path)
            except OSError:
                continue
            if not stat.S_ISREG(st.st_mode):
                continue
            if st.st_size < 1024:  # tiny files are unlikely to be interesting binaries
                continue
            try:
                with open(path, "rb") as f:
                    head = f.read(4)
            except OSError:
                continue
            if head == b"\x7fELF":
                elf_bins.append(path)
    return elf_bins


def _run_build_script(root: str, timeout: int = 180):
    # Look for common build script names at root
    candidates = ["build.sh", "build.bash", "build"]
    for name in candidates:
        path = os.path.join(root, name)
        if os.path.isfile(path):
            try:
                subprocess.run(
                    ["bash", path],
                    cwd=root,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=timeout,
                    check=False,
                )
            except Exception:
                pass
            break


def _select_binary_pair(elf_bins):
    if not elf_bins or len(elf_bins) < 2:
        return None, None

    vuln_tags = ("vuln", "bug", "old", "unsafe", "uaf")
    fix_tags = ("fix", "patched", "new", "safe", "fixed")

    def has_tag(name, tags):
        lname = name.lower()
        return any(t in lname for t in tags)

    vuln_list = [p for p in elf_bins if has_tag(os.path.basename(p), vuln_tags)]
    fix_list = [p for p in elf_bins if has_tag(os.path.basename(p), fix_tags)]

    if vuln_list and fix_list:
        best_pair = None
        best_score = None
        for v in vuln_list:
            for f in fix_list:
                score = 0
                if os.path.dirname(v) == os.path.dirname(f):
                    score -= 10
                score += abs(len(v) - len(f))
                if best_score is None or score < best_score:
                    best_score = score
                    best_pair = (v, f)
        if best_pair:
            return best_pair

    # Fallback: just take first two binaries sorted by path
    elf_bins_sorted = sorted(elf_bins)
    return elf_bins_sorted[0], elf_bins_sorted[1]


def _extract_phpt_script(data: bytes):
    # Very small parser: extract bytes between --FILE-- and the next --XXXX-- marker
    marker_file = b"--FILE--"
    idx = data.find(marker_file)
    if idx == -1:
        return None
    # Find end of the line containing --FILE--
    line_end = data.find(b"\n", idx)
    if line_end == -1:
        line_end = idx + len(marker_file)
    body = data[line_end + 1 :]
    # Find next marker line of the form \n--XXXX--
    m = re.search(rb"\n--[A-Z]+(--|F)--", body)
    if m:
        script = body[: m.start()]
    else:
        # No further marker; take rest
        script = body
    script = script.strip(b"\r\n")
    if script:
        return script
    return None


def _file_contains_div_zero(data: bytes) -> bool:
    # Look for "/=" followed by "0" within a short distance
    pos = 0
    while True:
        idx = data.find(b"/=", pos)
        if idx == -1:
            break
        window = data[idx : idx + 10]
        if b"0" in window:
            return True
        pos = idx + 2
    if b"division by zero" in data.lower() or b"divide by zero" in data.lower():
        return True
    return False


def _collect_pattern_candidates(root: str, max_candidates: int = 80):
    candidates = []
    seen = set()

    skip_exts = {
        ".o",
        ".a",
        ".so",
        ".dll",
        ".dylib",
        ".png",
        ".jpg",
        ".jpeg",
        ".gif",
        ".bmp",
        ".ico",
        ".pdf",
        ".zip",
        ".gz",
        ".bz2",
        ".xz",
        ".7z",
        ".tar",
        ".tgz",
        ".rar",
        ".mp3",
        ".mp4",
        ".avi",
        ".mov",
    }

    for dirpath, dirnames, filenames in os.walk(root):
        for fname in filenames:
            path = os.path.join(dirpath, fname)
            lower = fname.lower()
            _, ext = os.path.splitext(lower)
            if ext in skip_exts:
                continue
            try:
                st = os.stat(path)
            except OSError:
                continue
            if st.st_size > 64 * 1024:
                continue
            try:
                with open(path, "rb") as f:
                    data = f.read()
            except OSError:
                continue

            if not _file_contains_div_zero(data):
                continue

            snippet = None
            if lower.endswith(".phpt"):
                snippet = _extract_phpt_script(data)
            if snippet is None:
                if st.st_size <= 2048:
                    snippet = data
                else:
                    # Take context around "/="
                    idx = data.find(b"/=")
                    if idx == -1:
                        # fallback: around 'divide by zero'
                        kw = b"division by zero"
                        idx = data.lower().find(kw)
                    if idx == -1:
                        snippet = data[:2048]
                    else:
                        start = max(0, idx - 120)
                        end = min(len(data), idx + 200)
                        snippet = data[start:end]

            if not snippet:
                continue
            if snippet in seen:
                continue
            seen.add(snippet)
            candidates.append(snippet)
            if len(candidates) >= max_candidates:
                return candidates
    return candidates


def _generic_candidates():
    cands = [
        b"1/0\n",
        b"1 / 0\n",
        b"1 /= 0\n",
        b"a=1;a/=0;\n",
        b"a = 1; a /= 0;\n",
        b"var a = 1; a /= 0;\n",
        b"let a = 1; a /= 0;\n",
        b"$a = 1; $a /= 0;\n",
        b"$a=1;$a/=0;\n",
        b"<?php $a = 1; $a /= 0; ?>\n",
        b"<?php\n$a = 1;\n$a /= 0;\n?>\n",
        b"a=1\nb=0\na/=b\n",
        b"function f(){var a=1;a/=0;}f();\n",
        b"int main(){volatile int x=1; x/=0; return 0;}\n",
        b"print(1/0)\n",
        b"a=1\ntry:\n    a/=0\nexcept Exception as e:\n    print(e)\n",
        b"class C{public static function run(){ $a = 1; $a /= 0; }} C::run();\n",
    ]
    # Deduplicate while preserving order
    seen = set()
    uniq = []
    for c in cands:
        if c not in seen:
            seen.add(c)
            uniq.append(c)
    return uniq


def _run_binary(bin_path: str, data: bytes, style: str, timeout: float = 0.7):
    tmpfile = None
    try:
        if style == "stdin":
            try:
                p = subprocess.run(
                    [bin_path],
                    input=data,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=timeout,
                )
            except subprocess.TimeoutExpired:
                return "timeout", b"", b""
            except Exception:
                return "error", b"", b""
            return p.returncode, p.stdout, p.stderr
        elif style == "arg":
            import tempfile as _tempfile

            with _tempfile.NamedTemporaryFile(delete=False) as tf:
                tmpfile = tf.name
                tf.write(data)
            try:
                p = subprocess.run(
                    [bin_path, tmpfile],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=timeout,
                )
            except subprocess.TimeoutExpired:
                return "timeout", b"", b""
            except Exception:
                return "error", b"", b""
            return p.returncode, p.stdout, p.stderr
        elif style == "fuzz":
            import tempfile as _tempfile

            with _tempfile.NamedTemporaryFile(delete=False) as tf:
                tmpfile = tf.name
                tf.write(data)
            try:
                p = subprocess.run(
                    [bin_path, "-runs=1", tmpfile],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=max(timeout, 1.0),
                )
            except subprocess.TimeoutExpired:
                return "timeout", b"", b""
            except Exception:
                return "error", b"", b""
            return p.returncode, p.stdout, p.stderr
        else:
            return "error", b"", b""
    finally:
        if tmpfile is not None:
            try:
                os.unlink(tmpfile)
            except OSError:
                pass


def _is_bug_crash(retcode, stderr: bytes):
    if not isinstance(retcode, int):
        return False
    if retcode < 0:
        return True
    if retcode != 0:
        lower = stderr.lower()
        if (
            b"addresssanitizer" in lower
            or b"use-after-free" in lower
            or b"heap-use-after-free" in lower
            or b"heap-use-after-free" in stderr
        ):
            return True
    return False


class Solution:
    def solve(self, src_path: str) -> bytes:
        extract_dir = _extract_tarball(src_path)

        try:
            elf_bins = _find_elf_binaries(extract_dir)
            if not elf_bins:
                _run_build_script(extract_dir)
                elf_bins = _find_elf_binaries(extract_dir)

            vuln_bin, fixed_bin = _select_binary_pair(elf_bins)

            pattern_candidates = _collect_pattern_candidates(extract_dir)
            generic_candidates = _generic_candidates()

            # Assemble candidate list with pattern-based first
            candidates = []
            seen = set()
            for c in pattern_candidates + generic_candidates:
                if c not in seen:
                    seen.add(c)
                    candidates.append(c)

            io_styles = ["stdin", "arg", "fuzz"]

            selected_poc = None

            if vuln_bin and fixed_bin:
                for cand in candidates:
                    for style in io_styles:
                        v_ret, v_out, v_err = _run_binary(vuln_bin, cand, style)
                        if _is_bug_crash(v_ret, v_err):
                            f_ret, f_out, f_err = _run_binary(fixed_bin, cand, style)
                            if isinstance(f_ret, int) and f_ret == 0:
                                # Try simple minimization: strip whitespace
                                stripped = cand.strip(b"\x00 \t\r\n")
                                if stripped and stripped != cand:
                                    v_ret2, v_out2, v_err2 = _run_binary(
                                        vuln_bin, stripped, style
                                    )
                                    if _is_bug_crash(v_ret2, v_err2):
                                        f_ret2, f_out2, f_err2 = _run_binary(
                                            fixed_bin, stripped, style
                                        )
                                        if isinstance(f_ret2, int) and f_ret2 == 0:
                                            cand = stripped
                                selected_poc = cand
                                break
                    if selected_poc is not None:
                        break

            if selected_poc is None:
                # Fallback to a generic divide-by-zero candidate
                # Prefer a short, language-agnostic form
                fallback = b"a=1;a/=0;\n"
                selected_poc = fallback

            return selected_poc
        finally:
            try:
                shutil.rmtree(extract_dir)
            except Exception:
                pass
