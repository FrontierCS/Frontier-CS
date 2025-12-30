import os
import tarfile
import tempfile
import subprocess
import stat
import shutil


class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.
        """
        # Try to use dynamic analysis if a fuzzing binary is available.
        project_root = None
        temp_root = None

        if os.path.isdir(src_path):
            project_root = src_path
        else:
            temp_root = tempfile.mkdtemp(prefix="pocgen_src_")
            project_root = temp_root
            try:
                try:
                    with tarfile.open(src_path, "r:*") as tar:
                        tar.extractall(temp_root)
                except tarfile.TarError:
                    # Not a valid tar archive; ignore and treat as empty dir.
                    pass
                except Exception:
                    # Any extraction error, ignore dynamic approach.
                    pass
            except Exception:
                pass

        poc = None
        try:
            if project_root and os.path.isdir(project_root):
                bin_path = self._find_executable_binary(project_root)
                if bin_path:
                    is_libfuzzer = self._is_libfuzzer_binary(bin_path)
                    poc = self._search_for_crash(bin_path, is_libfuzzer)
        finally:
            # Clean up extracted sources if we created a temp directory.
            if temp_root is not None:
                shutil.rmtree(temp_root, ignore_errors=True)

        # If dynamic search found a crashing input, return it.
        if poc is not None:
            return poc

        # Fallback: generic long string intended to trigger length-related issues.
        return b"A" * 100 + b"\x00"

    # ---------------- Internal helpers ----------------

    def _find_executable_binary(self, root: str) -> str | None:
        """
        Recursively search for an executable binary that looks like a fuzz target.
        """
        best = None
        best_score = -1

        for dirpath, dirnames, filenames in os.walk(root):
            # Skip some common large or irrelevant directories.
            base = os.path.basename(dirpath)
            if base in (".git", ".svn", "build", "out", "__pycache__"):
                continue

            for name in filenames:
                full_path = os.path.join(dirpath, name)
                try:
                    st = os.stat(full_path)
                except OSError:
                    continue

                if not stat.S_ISREG(st.st_mode):
                    continue
                if not (st.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)):
                    continue

                # Skip obvious scripts.
                try:
                    with open(full_path, "rb") as f:
                        magic = f.read(4)
                    if magic.startswith(b"#!"):
                        continue
                except OSError:
                    continue

                # Heuristic scoring: prefer fuzz-like, dash-related binaries.
                score = 0
                lname = name.lower()
                if "fuzz" in lname or "fuzzer" in lname:
                    score += 5
                if "dash" in lname:
                    score += 3
                if "client" in lname:
                    score += 2
                if "." not in name:
                    score += 1

                size_kb = st.st_size // 1024
                if size_kb > 0:
                    score += min(size_kb // 50, 5)

                if score > best_score:
                    best_score = score
                    best = full_path

        return best

    def _is_libfuzzer_binary(self, bin_path: str) -> bool:
        """
        Heuristically detect if the binary is a libFuzzer target.
        """
        try:
            with open(bin_path, "rb") as f:
                data = f.read(2_000_000)
            if b"LLVMFuzzerTestOneInput" in data or b"libFuzzer" in data:
                return True
        except OSError:
            pass
        return False

    def _search_for_crash(self, bin_path: str, is_libfuzzer: bool) -> bytes | None:
        """
        Try a small set of candidate inputs against the binary and look for ASan/UBSan crashes.
        """
        candidates = list(self._generate_candidates())

        workdir = tempfile.mkdtemp(prefix="pocgen_inputs_")
        try:
            for idx, data in enumerate(candidates):
                inpath = os.path.join(workdir, f"input_{idx}")
                try:
                    with open(inpath, "wb") as f:
                        f.write(data)
                except OSError:
                    continue

                if self._run_and_check_crash(bin_path, inpath, data, is_libfuzzer):
                    return data
        finally:
            shutil.rmtree(workdir, ignore_errors=True)

        return None

    def _run_and_check_crash(
        self,
        bin_path: str,
        inpath: str,
        data: bytes,
        is_libfuzzer: bool,
    ) -> bool:
        """
        Run the target with a given input file and detect sanitizer crashes.
        """
        env = os.environ.copy()
        asan_opts = env.get("ASAN_OPTIONS", "")
        extra_opts = ["detect_leaks=0", "halt_on_error=1", "abort_on_error=1"]
        for opt in extra_opts:
            key = opt.split("=", 1)[0]
            if key not in asan_opts:
                if asan_opts and not asan_opts.endswith(":"):
                    asan_opts += ":"
                asan_opts += opt
        if asan_opts:
            env["ASAN_OPTIONS"] = asan_opts

        # Choose command-line based on binary type.
        if is_libfuzzer:
            cmd = [bin_path, "-runs=1", inpath]
        else:
            cmd = [bin_path, inpath]

        try:
            proc = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                env=env,
                timeout=0.5,
            )
        except (subprocess.TimeoutExpired, OSError, ValueError):
            return False

        if proc.returncode == 0:
            return False

        combined = proc.stdout + proc.stderr
        low = combined.lower()

        # Detect typical sanitizer outputs.
        if b"heap-buffer-overflow" in low:
            return True
        if b"addresssanitizer" in low and b"overflow" in low:
            return True
        if b"asan" in low and b"overflow" in low:
            return True
        if b"ubsan" in low or b"runtime error" in low:
            return True
        if b"sanitizer" in low and b"error" in low:
            return True

        return False

    def _generate_candidates(self):
        """
        Generate a series of candidate inputs. Ordered from shorter to longer to
        favor shorter PoCs when possible.
        """

        # Very short uniform strings (including length 9 near the beginning).
        for n in range(1, 13):
            yield b"A" * n
        yield b"B" * 9
        yield b"A" * 8 + b"\x00"
        yield b"A" * 9 + b"\x00"

        # A few mid-size uniform strings.
        for n in (16, 24, 32, 40, 48, 56, 64):
            yield b"A" * n
        for n in (16, 32, 64):
            yield b"A" * n + b"\x00"

        # HTTP-like requests with long paths (common for client-style parsers).
        base_req = b"GET /"
        for path_len in (8, 16, 32, 64):
            path = b"A" * path_len
            req = (
                base_req
                + path
                + b" HTTP/1.1\r\nHost: example.com\r\nUser-Agent: dash_client_poc\r\n\r\n"
            )
            yield req

        # Headers that might be processed by dash client.
        for val_len in (8, 16, 32, 64, 128):
            yield b"Dash-Client: " + (b"A" * val_len) + b"\r\n"

        # Larger uniform strings aimed at overflowing small/medium buffers.
        for n in (80, 96, 128, 192, 256, 512, 1024):
            yield b"A" * n + b"\x00"

        # Final generic long string (also used as fallback if nothing crashes).
        yield b"A" * 100 + b"\x00"