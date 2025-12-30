import os
import re
import io
import sys
import tarfile
import shutil
import struct
import random
import tempfile
import subprocess
from typing import List, Optional, Tuple


_FDP_HEADER = r'''
#ifndef FUZZED_DATA_PROVIDER_H_
#define FUZZED_DATA_PROVIDER_H_

#include <algorithm>
#include <cassert>
#include <cctype>
#include <cmath>
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <initializer_list>
#include <limits>
#include <string>
#include <type_traits>
#include <utility>
#include <vector>

class FuzzedDataProvider {
 public:
  FuzzedDataProvider(const uint8_t *data, size_t size)
      : data_ptr_(data), remaining_bytes_(size) {}

  size_t remaining_bytes() const { return remaining_bytes_; }

  template <typename T>
  T ConsumeIntegral() {
    static_assert(std::is_integral<T>::value, "T must be integral.");
    if (remaining_bytes_ < sizeof(T)) return 0;
    T out;
    std::memcpy(&out, data_ptr_, sizeof(T));
    Advance(sizeof(T));
    return out;
  }

  template <typename T>
  T ConsumeIntegralInRange(T min, T max) {
    static_assert(std::is_integral<T>::value, "T must be integral.");
    if (min > max) std::swap(min, max);
    const auto range = static_cast<std::make_unsigned_t<T>>(max - min);
    if (range == 0) return min;
    const auto val = static_cast<std::make_unsigned_t<T>>(ConsumeIntegral<std::make_unsigned_t<T>>());
    return static_cast<T>(min + static_cast<T>(val % (range + 1)));
  }

  bool ConsumeBool() { return ConsumeIntegralInRange<uint8_t>(0, 1) == 1; }

  template <typename T>
  T ConsumeFloatingPoint() {
    static_assert(std::is_floating_point<T>::value, "T must be floating point.");
    if (remaining_bytes_ < sizeof(T)) return 0;
    T out;
    std::memcpy(&out, data_ptr_, sizeof(T));
    Advance(sizeof(T));
    if (std::isnan(out) || std::isinf(out)) return static_cast<T>(0);
    if (out < static_cast<T>(0)) out = -out;
    out = std::fmod(out, static_cast<T>(1.0));
    if (out < static_cast<T>(0)) out = -out;
    if (out >= static_cast<T>(1.0)) out = static_cast<T>(0);
    return out;
  }

  template <typename T>
  T ConsumeFloatingPointInRange(T min, T max) {
    static_assert(std::is_floating_point<T>::value, "T must be floating point.");
    if (min > max) std::swap(min, max);
    const T range = max - min;
    if (range == static_cast<T>(0)) return min;
    const T unit = ConsumeFloatingPoint<T>();  // [0,1)
    return min + unit * range;
  }

  template <typename T>
  std::vector<T> ConsumeBytes(size_t num_bytes) {
    static_assert(std::is_trivial<T>::value, "T must be trivial.");
    if (num_bytes == 0) return {};
    const size_t max_bytes = remaining_bytes_;
    num_bytes = std::min(num_bytes, max_bytes);
    const size_t num_elems = num_bytes / sizeof(T);
    std::vector<T> out(num_elems);
    std::memcpy(out.data(), data_ptr_, num_elems * sizeof(T));
    Advance(num_elems * sizeof(T));
    return out;
  }

  template <typename T>
  std::vector<T> ConsumeRemainingBytes() {
    return ConsumeBytes<T>(remaining_bytes_);
  }

  std::string ConsumeBytesAsString(size_t num_bytes) {
    auto v = ConsumeBytes<char>(num_bytes);
    return std::string(v.begin(), v.end());
  }

  std::string ConsumeRemainingBytesAsString() {
    return ConsumeBytesAsString(remaining_bytes_);
  }

  std::string ConsumeRandomLengthString(size_t max_length) {
    if (max_length == 0) return std::string();
    const size_t len = ConsumeIntegralInRange<size_t>(0, max_length);
    return ConsumeBytesAsString(len);
  }

  template <typename T>
  T PickValueInArray(const std::initializer_list<T>& list) {
    if (list.size() == 0) return T();
    const size_t idx = ConsumeIntegralInRange<size_t>(0, list.size() - 1);
    return *(list.begin() + idx);
  }

  template <typename T>
  T ConsumeEnum() {
    static_assert(std::is_enum<T>::value, "T must be enum.");
    using U = typename std::underlying_type<T>::type;
    return static_cast<T>(ConsumeIntegral<U>());
  }

 private:
  void Advance(size_t num_bytes) {
    assert(num_bytes <= remaining_bytes_);
    remaining_bytes_ -= num_bytes;
    data_ptr_ += num_bytes;
  }

  const uint8_t* data_ptr_;
  size_t remaining_bytes_;
};

#endif  // FUZZED_DATA_PROVIDER_H_
'''.lstrip()


def _safe_extract_tar(tar_path: str, dst_dir: str) -> None:
    def is_within_directory(directory: str, target: str) -> bool:
        abs_directory = os.path.abspath(directory)
        abs_target = os.path.abspath(target)
        return os.path.commonpath([abs_directory]) == os.path.commonpath([abs_directory, abs_target])

    with tarfile.open(tar_path, 'r:*') as tar:
        for member in tar.getmembers():
            member_path = os.path.join(dst_dir, member.name)
            if not is_within_directory(dst_dir, member_path):
                continue
            tar.extract(member, dst_dir)


def _find_project_root(extracted_dir: str) -> str:
    entries = [os.path.join(extracted_dir, x) for x in os.listdir(extracted_dir)]
    dirs = [p for p in entries if os.path.isdir(p)]
    if len(dirs) == 1 and not any(os.path.isfile(p) for p in entries):
        return dirs[0]
    return extracted_dir


def _iter_source_files(root: str) -> List[str]:
    out = []
    for base, _, files in os.walk(root):
        for fn in files:
            lfn = fn.lower()
            if lfn.endswith(('.c', '.cc', '.cpp', '.cxx', '.h', '.hpp', '.hh')):
                out.append(os.path.join(base, fn))
    return out


def _file_contains(path: str, needles: List[bytes], max_bytes: int = 2_000_000) -> bool:
    try:
        with open(path, 'rb') as f:
            data = f.read(max_bytes)
        return all(n in data for n in needles)
    except Exception:
        return False


def _find_fuzzer_source(root: str) -> Optional[str]:
    candidates = []
    for p in _iter_source_files(root):
        if not p.lower().endswith(('.c', '.cc', '.cpp', '.cxx')):
            continue
        if _file_contains(p, [b'LLVMFuzzerTestOneInput']):
            candidates.append(p)

    def score(path: str) -> int:
        s = 0
        try:
            with open(path, 'rb') as f:
                data = f.read(500_000)
        except Exception:
            return -10
        if b'polygonToCellsExperimental' in data:
            s += 100
        if b'maxPolygonToCellsSizeExperimental' in data:
            s += 50
        if b'GeoPolygon' in data or b'Geofence' in data:
            s += 10
        if b'FuzzedDataProvider' in data:
            s += 5
        if b'H3' in data or b'h3' in data:
            s += 1
        return s

    if candidates:
        candidates.sort(key=score, reverse=True)
        best = candidates[0]
        if score(best) > 0:
            return best

    # Fallback: file that calls polygonToCellsExperimental, may have different entry setup
    for p in _iter_source_files(root):
        if not p.lower().endswith(('.c', '.cc', '.cpp', '.cxx')):
            continue
        if _file_contains(p, [b'polygonToCellsExperimental']):
            return p
    return None


def _write_fdp_headers(incdir: str) -> None:
    os.makedirs(incdir, exist_ok=True)
    with open(os.path.join(incdir, "FuzzedDataProvider.h"), "w", encoding="utf-8") as f:
        f.write(_FDP_HEADER)
    fuzzer_dir = os.path.join(incdir, "fuzzer")
    os.makedirs(fuzzer_dir, exist_ok=True)
    with open(os.path.join(fuzzer_dir, "FuzzedDataProvider.h"), "w", encoding="utf-8") as f:
        f.write(_FDP_HEADER)


def _which(cmd: str) -> Optional[str]:
    return shutil.which(cmd)


def _run(cmd: List[str], cwd: Optional[str] = None, env: Optional[dict] = None, timeout: Optional[int] = None) -> Tuple[int, str, str]:
    p = subprocess.run(
        cmd,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        timeout=timeout,
        text=True,
        errors="replace",
    )
    return p.returncode, p.stdout, p.stderr


def _detect_h3_include_dirs(root: str) -> List[str]:
    incs = []
    for base, _, files in os.walk(root):
        for fn in files:
            if fn == "h3api.h":
                incs.append(base)
    # common extra include dirs
    for cand in [
        os.path.join(root, "src", "h3lib", "include"),
        os.path.join(root, "include"),
        os.path.join(root, "src", "include"),
    ]:
        if os.path.isdir(cand):
            incs.append(cand)
    # de-dup
    seen = set()
    out = []
    for p in incs:
        ap = os.path.abspath(p)
        if ap not in seen:
            seen.add(ap)
            out.append(ap)
    return out


def _collect_h3_c_sources(root: str) -> List[str]:
    # Prefer canonical H3 layout
    preferred = []
    for cand in [
        os.path.join(root, "src", "h3lib", "lib"),
        os.path.join(root, "src", "h3lib"),
        os.path.join(root, "h3lib", "lib"),
        os.path.join(root, "h3lib"),
    ]:
        if os.path.isdir(cand):
            for base, _, files in os.walk(cand):
                for fn in files:
                    if fn.lower().endswith(".c"):
                        preferred.append(os.path.join(base, fn))
            if preferred:
                break

    if preferred:
        # filter obvious mains under apps
        out = []
        for p in preferred:
            lp = p.replace("\\", "/").lower()
            if "/app" in lp or "/apps/" in lp or "/test" in lp or "/tests/" in lp or "/fuzz" in lp or "/fuzzer" in lp:
                continue
            out.append(p)
        if out:
            return out
        return preferred

    # fallback: all .c not in tests/apps/fuzz
    out = []
    for base, _, files in os.walk(root):
        for fn in files:
            if not fn.lower().endswith(".c"):
                continue
            p = os.path.join(base, fn)
            lp = p.replace("\\", "/").lower()
            if any(x in lp for x in ["/test", "/tests/", "/example", "/examples/", "/app", "/apps/", "/fuzz", "/fuzzer", "/bench"]):
                continue
            out.append(p)
    return out


def _find_config_header_dirs(root: str) -> List[str]:
    dirs = []
    for base, _, files in os.walk(root):
        if "config.h" in files:
            dirs.append(base)
    # de-dup
    seen = set()
    out = []
    for d in dirs:
        ad = os.path.abspath(d)
        if ad not in seen:
            seen.add(ad)
            out.append(ad)
    return out


def _build_libfuzzer_exe(root: str, fuzzer_src: str, workdir: str) -> Optional[str]:
    clang = _which("clang")
    clangxx = _which("clang++")
    if not clangxx or not clang:
        return None

    inc_override = os.path.join(workdir, "inc_override")
    _write_fdp_headers(inc_override)

    incs = [inc_override] + _detect_h3_include_dirs(root) + _find_config_header_dirs(root) + [root, os.path.dirname(fuzzer_src)]
    inc_flags = []
    for i in incs:
        inc_flags += ["-I", i]

    c_sources = _collect_h3_c_sources(root)
    if not c_sources:
        return None

    build_dir = os.path.join(workdir, "build")
    os.makedirs(build_dir, exist_ok=True)

    cflags = ["-O1", "-g", "-fno-omit-frame-pointer", "-fno-optimize-sibling-calls"]
    san = ["-fsanitize=address,undefined"]
    cflags += san
    cxxflags = ["-std=c++17"] + cflags
    ldflags = ["-fsanitize=fuzzer,address,undefined"]

    objs = []
    # Compile C sources
    for idx, src in enumerate(c_sources):
        obj = os.path.join(build_dir, f"c_{idx}.o")
        cmd = [clang, "-c", src, "-o", obj] + cflags + inc_flags
        rc, _, err = _run(cmd, cwd=root)
        if rc != 0:
            # Try with -DH3_* common fallbacks
            cmd2 = cmd + ["-DH3_HAVE_VLA=1"]
            rc2, _, _ = _run(cmd2, cwd=root)
            if rc2 != 0:
                return None
        objs.append(obj)

    # Compile fuzzer source
    fuzzer_obj = os.path.join(build_dir, "fuzzer.o")
    cmd = [clangxx, "-c", fuzzer_src, "-o", fuzzer_obj] + cxxflags + inc_flags
    rc, _, _ = _run(cmd, cwd=root)
    if rc != 0:
        # Try as C
        cmd = [clang, "-c", fuzzer_src, "-o", fuzzer_obj] + cflags + inc_flags
        rc, _, _ = _run(cmd, cwd=root)
        if rc != 0:
            return None

    exe = os.path.join(build_dir, "fuzzer_exe")
    link_cmd = [clangxx, "-o", exe] + objs + [fuzzer_obj] + ldflags + ["-lm", "-lpthread"]
    rc, _, _ = _run(link_cmd, cwd=root)
    if rc != 0:
        # Try without ubsan if toolchain conflicts
        ldflags2 = ["-fsanitize=fuzzer,address"]
        link_cmd2 = [clangxx, "-o", exe] + objs + [fuzzer_obj] + ldflags2 + ["-lm", "-lpthread"]
        rc2, _, _ = _run(link_cmd2, cwd=root)
        if rc2 != 0:
            return None
    return exe


def _list_artifacts(artifact_dir: str) -> List[str]:
    if not os.path.isdir(artifact_dir):
        return []
    files = []
    for fn in os.listdir(artifact_dir):
        p = os.path.join(artifact_dir, fn)
        if os.path.isfile(p) and (fn.startswith("crash-") or fn.startswith("leak-") or fn.startswith("timeout-") or fn.startswith("oom-") or fn.startswith("artifact")):
            files.append(p)
    files.sort(key=lambda p: os.path.getmtime(p), reverse=True)
    return files


def _run_fuzzer_find_crash(exe: str, workdir: str, max_total_time: int) -> Optional[bytes]:
    corpus = os.path.join(workdir, "corpus")
    artifact = os.path.join(workdir, "artifacts")
    os.makedirs(corpus, exist_ok=True)
    os.makedirs(artifact, exist_ok=True)

    # Seed corpus
    seeds = [
        b"",
        b"\x00" * 2048,
        b"\xff" * 2048,
        bytes([0x00, 0xff]) * 1024,
        bytes(range(256)) * 8,
    ]
    rng = random.Random(12345)
    seeds.append(bytes(rng.getrandbits(8) for _ in range(2048)))
    for i, s in enumerate(seeds):
        with open(os.path.join(corpus, f"seed_{i}"), "wb") as f:
            f.write(s)

    env = os.environ.copy()
    env["ASAN_OPTIONS"] = env.get("ASAN_OPTIONS", "") + ":abort_on_error=1:halt_on_error=1:detect_leaks=0:symbolize=0"
    env["UBSAN_OPTIONS"] = env.get("UBSAN_OPTIONS", "") + ":abort_on_error=1:halt_on_error=1:symbolize=0"

    cmd = [
        exe,
        f"-artifact_prefix={artifact}{os.sep}",
        "-max_len=8192",
        "-timeout=3",
        "-rss_limit_mb=0",
        "-seed=1",
        f"-max_total_time={max_total_time}",
        corpus,
    ]
    rc, out, err = _run(cmd, cwd=workdir, env=env, timeout=max_total_time + 30)

    arts = _list_artifacts(artifact)
    if arts:
        with open(arts[0], "rb") as f:
            return f.read()

    # Sometimes libFuzzer writes artifact path only to output without prefix match; try parse
    m = re.search(r"(?:Test unit written to|artifact_prefix=.*?)([^\s]+(?:crash|timeout|oom|leak)[^\s]*)", out + "\n" + err)
    if m:
        p = m.group(1)
        if os.path.isfile(p):
            with open(p, "rb") as f:
                return f.read()

    # If rc indicates crash but artifact missing, no luck
    return None


def _run_single_input(exe: str, inp: bytes, workdir: str) -> bool:
    path = os.path.join(workdir, "one_input")
    with open(path, "wb") as f:
        f.write(inp)

    env = os.environ.copy()
    env["ASAN_OPTIONS"] = env.get("ASAN_OPTIONS", "") + ":abort_on_error=1:halt_on_error=1:detect_leaks=0:symbolize=0"
    env["UBSAN_OPTIONS"] = env.get("UBSAN_OPTIONS", "") + ":abort_on_error=1:halt_on_error=1:symbolize=0"
    rc, _, _ = _run([exe, path], cwd=workdir, env=env, timeout=10)
    return rc != 0


def _libfuzzer_minimize(exe: str, inp: bytes, workdir: str) -> bytes:
    if not inp:
        return inp
    inpath = os.path.join(workdir, "crash_input")
    outpath = os.path.join(workdir, "minimized")
    with open(inpath, "wb") as f:
        f.write(inp)

    env = os.environ.copy()
    env["ASAN_OPTIONS"] = env.get("ASAN_OPTIONS", "") + ":abort_on_error=1:halt_on_error=1:detect_leaks=0:symbolize=0"
    env["UBSAN_OPTIONS"] = env.get("UBSAN_OPTIONS", "") + ":abort_on_error=1:halt_on_error=1:symbolize=0"

    cmd = [
        exe,
        "-minimize_crash=1",
        f"-exact_artifact_path={outpath}",
        "-timeout=3",
        inpath,
    ]
    try:
        _run(cmd, cwd=workdir, env=env, timeout=60)
    except Exception:
        return inp
    if os.path.isfile(outpath):
        try:
            with open(outpath, "rb") as f:
                return f.read()
        except Exception:
            return inp
    return inp


class Solution:
    def solve(self, src_path: str) -> bytes:
        with tempfile.TemporaryDirectory(prefix="pocgen_") as td:
            if os.path.isdir(src_path):
                root = src_path
            else:
                extract_dir = os.path.join(td, "src")
                os.makedirs(extract_dir, exist_ok=True)
                try:
                    _safe_extract_tar(src_path, extract_dir)
                except Exception:
                    # If it's not a tarball, treat as raw bytes path (unlikely)
                    return b"\x00" * 1032
                root = _find_project_root(extract_dir)

            fuzzer_src = _find_fuzzer_source(root)
            if not fuzzer_src:
                return b"\x00" * 1032

            workdir = os.path.join(td, "work")
            os.makedirs(workdir, exist_ok=True)

            exe = _build_libfuzzer_exe(root, fuzzer_src, workdir)
            if not exe or not os.path.isfile(exe):
                return b"\x00" * 1032

            # Try several time budgets deterministically.
            for t in (10, 25, 60, 120):
                poc = _run_fuzzer_find_crash(exe, workdir, max_total_time=t)
                if poc is None:
                    continue
                # Ensure it crashes (avoid spurious artifacts)
                if not _run_single_input(exe, poc, workdir):
                    continue
                poc2 = _libfuzzer_minimize(exe, poc, workdir)
                if poc2 and _run_single_input(exe, poc2, workdir):
                    return poc2
                return poc

            return b"\x00" * 1032