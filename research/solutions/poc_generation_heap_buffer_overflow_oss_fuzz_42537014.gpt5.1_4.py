import os
import tarfile
import tempfile
import subprocess
import shutil
from typing import Optional, List
import zipfile
import random


class Solution:
    def solve(self, src_path: str) -> bytes:
        src_root, work_dir = self._prepare_src(src_path)
        poc = self._build_and_find_poc(src_root, work_dir)
        if poc is not None:
            return poc
        return b"A" * 9

    def _prepare_src(self, src_path: str):
        work_dir = tempfile.mkdtemp(prefix="poc_gen_")
        if os.path.isdir(src_path):
            src_root = src_path
            return src_root, work_dir

        extract_dir = os.path.join(work_dir, "src")
        os.makedirs(extract_dir, exist_ok=True)

        extracted = False
        if tarfile.is_tarfile(src_path):
            try:
                with tarfile.open(src_path) as tf:
                    tf.extractall(extract_dir)
                extracted = True
            except Exception:
                extracted = False

        if not extracted:
            try:
                with zipfile.ZipFile(src_path) as zf:
                    zf.extractall(extract_dir)
                extracted = True
            except Exception:
                extracted = False

        if not extracted:
            src_root = os.path.dirname(os.path.abspath(src_path))
            return src_root, work_dir

        entries = [e for e in os.listdir(extract_dir) if not e.startswith(".")]
        if len(entries) == 1:
            candidate = os.path.join(extract_dir, entries[0])
            if os.path.isdir(candidate):
                src_root = candidate
            else:
                src_root = extract_dir
        else:
            src_root = extract_dir
        return src_root, work_dir

    def _find_build_sh(self, root: str) -> Optional[str]:
        candidates: List[str] = []
        for dirpath, _, filenames in os.walk(root):
            if "build.sh" in filenames:
                candidates.append(os.path.join(dirpath, "build.sh"))
        if not candidates:
            return None
        candidates.sort(key=lambda p: p.count(os.sep))
        return candidates[0]

    def _find_compiler(self, names: List[str]) -> Optional[str]:
        for name in names:
            path = shutil.which(name)
            if path:
                return path
        return None

    def _find_fuzz_binary(self, out_dir: str) -> Optional[str]:
        best_score = None
        best_path = None
        for dirpath, _, filenames in os.walk(out_dir):
            for fname in filenames:
                path = os.path.join(dirpath, fname)
                if not os.path.isfile(path):
                    continue
                if not os.access(path, os.X_OK):
                    continue
                lname = fname.lower()
                score = 0
                if "dash" in lname:
                    score += 4
                if "client" in lname:
                    score += 2
                if "fuzz" in lname or "fuzzer" in lname:
                    score += 1
                if best_score is None or score > best_score:
                    best_score = score
                    best_path = path
        if best_path:
            return best_path

        for dirpath, _, filenames in os.walk(out_dir):
            for fname in filenames:
                path = os.path.join(dirpath, fname)
                if os.path.isfile(path) and os.access(path, os.X_OK):
                    return path
        return None

    def _build_and_find_poc(self, src_root: str, work_dir: str) -> Optional[bytes]:
        try:
            build_sh = self._find_build_sh(src_root)
            if not build_sh:
                return None

            cxx = self._find_compiler(["clang++", "g++", "c++"])
            if not cxx:
                return None

            if cxx.endswith("++"):
                cc = cxx[:-2]
            elif "g++" in cxx:
                cc = "gcc"
            else:
                cc = "clang"

            stub_dir = os.path.join(work_dir, "fuzz_stub")
            os.makedirs(stub_dir, exist_ok=True)
            stub_cc = os.path.join(stub_dir, "fuzzer_stub.cc")
            stub_obj = os.path.join(stub_dir, "fuzzer_stub.o")

            stub_code = r"""
#include <cstdint>
#include <cstddef>
#include <cstdio>
#include <vector>
#include <fstream>
#include <iostream>
#include <iterator>

extern "C" int LLVMFuzzerTestOneInput(const uint8_t *data, size_t size);

int main(int argc, char **argv) {
  std::vector<uint8_t> buffer;
  if (argc <= 1) {
    std::istreambuf_iterator<char> it(std::cin.rdbuf());
    std::istreambuf_iterator<char> end;
    for (; it != end; ++it) {
      buffer.push_back(static_cast<uint8_t>(*it));
    }
    LLVMFuzzerTestOneInput(buffer.data(), buffer.size());
  } else {
    for (int i = 1; i < argc; ++i) {
      std::ifstream ifs(argv[i], std::ios::binary);
      if (!ifs) continue;
      buffer.assign(std::istreambuf_iterator<char>(ifs),
                    std::istreambuf_iterator<char>());
      LLVMFuzzerTestOneInput(buffer.data(), buffer.size());
    }
  }
  return 0;
}
"""
            with open(stub_cc, "w") as f:
                f.write(stub_code)

            compile_cmd = [
                cxx,
                "-c",
                "-std=c++11",
                "-O1",
                "-g",
                "-fsanitize=address",
                stub_cc,
                "-o",
                stub_obj,
            ]
            subprocess.run(
                compile_cmd,
                cwd=stub_dir,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )

            env = os.environ.copy()
            env["CC"] = cc
            env["CXX"] = cxx

            base_flags = "-O1 -g -fsanitize=address"
            cflags = env.get("CFLAGS", "")
            if base_flags not in cflags:
                env["CFLAGS"] = (cflags + " " + base_flags).strip()
            cxxflags = env.get("CXXFLAGS", "")
            if base_flags not in cxxflags:
                env["CXXFLAGS"] = (cxxflags + " " + base_flags).strip()

            out_dir = os.path.join(work_dir, "out")
            os.makedirs(out_dir, exist_ok=True)
            env.setdefault("OUT", out_dir)
            env.setdefault("SANITIZER", "address")
            env.setdefault("SRC", src_root)
            env["LIB_FUZZING_ENGINE"] = stub_obj

            subprocess.run(
                ["bash", build_sh],
                cwd=os.path.dirname(build_sh),
                env=env,
                check=True,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                timeout=300,
            )

            bin_path = self._find_fuzz_binary(out_dir)
            if not bin_path:
                return None

            def causes_crash(data: bytes) -> bool:
                fd, tmp_path = tempfile.mkstemp(dir=work_dir)
                try:
                    with os.fdopen(fd, "wb") as f:
                        f.write(data)
                    try:
                        res = subprocess.run(
                            [bin_path, tmp_path],
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            timeout=10,
                        )
                    except subprocess.TimeoutExpired:
                        return False
                    return res.returncode != 0
                finally:
                    try:
                        os.remove(tmp_path)
                    except OSError:
                        pass

            for length in range(1, 65):
                data = b"A" * length
                if causes_crash(data):
                    return data

            random.seed(0)
            for _ in range(512):
                length = random.randint(1, 4096)
                data = os.urandom(length)
                if causes_crash(data):
                    return data

            return None
        except Exception:
            return None