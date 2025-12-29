import os
import tarfile
import tempfile
import subprocess
import shutil
import stat
import time


class Solution:
    def solve(self, src_path: str) -> bytes:
        try:
            poc = self._generate_poc(src_path)
            if poc:
                return poc
        except Exception:
            pass
        return self._fallback_poc()

    def _generate_poc(self, src_path: str) -> bytes | None:
        start_time = time.time()
        time_budget = 20.0  # seconds for dynamic work

        tmpdir = tempfile.mkdtemp(prefix="pocgen_")
        try:
            # Extract the tarball
            try:
                with tarfile.open(src_path, "r:*") as tf:
                    tf.extractall(tmpdir)
            except Exception:
                return None

            if time.time() - start_time > time_budget:
                return None

            out_dir = os.path.join(tmpdir, "out")
            os.makedirs(out_dir, exist_ok=True)

            # Locate build.sh scripts
            build_scripts = []
            for root, dirs, files in os.walk(tmpdir):
                if "build.sh" in files:
                    build_scripts.append(os.path.join(root, "build.sh"))

            if not build_scripts:
                return None

            env_base = os.environ.copy()
            env_base.setdefault("OUT", out_dir)

            built = False
            for bs in build_scripts:
                if time.time() - start_time > time_budget:
                    return None
                try:
                    r = subprocess.run(
                        ["bash", bs],
                        cwd=os.path.dirname(bs),
                        env=env_base,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=60,
                    )
                except subprocess.TimeoutExpired:
                    continue
                except Exception:
                    continue
                if r.returncode == 0:
                    built = True
                    break

            if not built:
                return None

            if time.time() - start_time > time_budget:
                return None

            binaries = self._find_binaries(out_dir)
            if not binaries:
                binaries = self._find_binaries(tmpdir)
            if not binaries:
                return None

            payloads = self._candidate_payloads()
            # Try only a few binaries to keep runtime manageable
            max_binaries = 3
            per_run_timeout = 0.1

            for bin_path in binaries[:max_binaries]:
                for payload in payloads:
                    if time.time() - start_time > time_budget:
                        return None
                    if self._run_and_check(bin_path, payload, per_run_timeout):
                        return payload

            return None
        finally:
            try:
                shutil.rmtree(tmpdir)
            except Exception:
                pass

    def _find_binaries(self, root: str) -> list:
        bins = []
        for dirpath, dirnames, filenames in os.walk(root):
            for fname in filenames:
                path = os.path.join(dirpath, fname)
                try:
                    st = os.stat(path)
                except Exception:
                    continue
                if not stat.S_ISREG(st.st_mode):
                    continue
                if not (st.st_mode & stat.S_IXUSR):
                    continue
                try:
                    with open(path, "rb") as f:
                        magic = f.read(4)
                except Exception:
                    continue
                if magic == b"\x7fELF":
                    bins.append(path)
        return bins

    def _candidate_payloads(self) -> list[bytes]:
        base_strings = [
            "-inf",
            "-Inf",
            "-INF",
            "-infinity",
            "-Infinity",
            "-INFINITY",
            "-infi",
            "-infa",
            "-inf0",
            "-inf1",
            "-inf.",
            "-inf..",
            "-infinity0",
            "-infinity1",
            "-infinity.",
            "-infinityx",
            "-inn",
            "-ni",
            "-nan",
            "-NaN",
            "-foo",
            "-bar",
            "-1",
            "-1.",
            "-1e",
            "-1e+",
            "-1e309",
            "--inf",
            "+-inf",
            "-+inf",
            "- inf",
        ]
        extras = [
            "",
            "\n",
            " ",
            "0",
            "00",
            "0000",
            "xxxx",
            "1234",
        ]

        payloads_set: set[bytes] = set()
        for s in base_strings:
            for e in extras:
                p = (s + e).encode("ascii", "ignore")
                if 1 <= len(p) <= 16:
                    payloads_set.add(p)

        # Some explicit 16-byte candidates closely tied to minus/infinity theme
        payloads_set.add(b"-infinity-000000")  # 16 bytes
        payloads_set.add(b"-inf-1234567890")   # 16 bytes
        payloads_set.add(b"-INF1234567890")    # 16 bytes

        payloads_list = sorted(payloads_set, key=lambda x: (len(x), x))
        return payloads_list

    def _run_and_check(self, bin_path: str, payload: bytes, timeout: float) -> bool:
        # First: try feeding via stdin
        try:
            r = subprocess.run(
                [bin_path],
                input=payload,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                timeout=timeout,
            )
            if self._is_crash(r):
                return True
        except subprocess.TimeoutExpired:
            pass
        except Exception:
            return False

        # Second: try via file argument
        tmp_file = None
        try:
            fd, tmp_file = tempfile.mkstemp(prefix="pocinput_", suffix=".bin")
            with os.fdopen(fd, "wb") as f:
                f.write(payload)
            try:
                r = subprocess.run(
                    [bin_path, tmp_file],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=timeout,
                )
            except subprocess.TimeoutExpired:
                return False
            except Exception:
                return False
            return self._is_crash(r)
        finally:
            if tmp_file is not None:
                try:
                    os.unlink(tmp_file)
                except Exception:
                    pass

    def _is_crash(self, result: subprocess.CompletedProcess) -> bool:
        rc = result.returncode
        if rc is None:
            return False
        # Crashed via signal
        if rc < 0:
            return True

        out = b""
        try:
            out = (result.stdout or b"") + (result.stderr or b"")
        except Exception:
            pass
        text = ""
        try:
            text = out.decode("latin1", errors="ignore")
        except Exception:
            pass

        crash_keywords = [
            "AddressSanitizer",
            "UndefinedBehaviorSanitizer",
            "runtime error",
            "stack-buffer-overflow",
            "heap-buffer-overflow",
            "stack smashing detected",
            "==ERROR:",
            "Sanitizer:",
            "Segmentation fault",
        ]
        for kw in crash_keywords:
            if kw in text:
                return True
        return False

    def _fallback_poc(self) -> bytes:
        # 16-byte payload themed around the described bug (minus + infinity)
        return b"-infinity-000000"