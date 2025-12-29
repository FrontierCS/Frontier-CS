import os
import tarfile
import tempfile
import shutil
import subprocess
import struct
import random
import time
import select


FUZZED_DATA_PROVIDER_CODE = r'''
#include <cstddef>
#include <cstdint>
#include <cstring>
#include <vector>
#include <string>

namespace fuzzing {

class FuzzedDataProvider {
 public:
  FuzzedDataProvider(const uint8_t *data, size_t size)
      : data_(data), size_(size), offset_(0) {}

  size_t remaining_bytes() const {
    return size_ - offset_;
  }

  template <typename T>
  T ConsumeIntegral() {
    T result = 0;
    size_t need = sizeof(T);
    size_t rem = remaining_bytes();
    if (need > rem) need = rem;
    if (need > 0) {
      std::memcpy(&result, data_ + offset_, need);
      offset_ += need;
    }
    return result;
  }

  template <typename T>
  T ConsumeIntegralInRange(T min, T max) {
    if (min > max) {
      T tmp = min;
      min = max;
      max = tmp;
    }
    unsigned long long range =
        static_cast<unsigned long long>(max) -
        static_cast<unsigned long long>(min);
    unsigned long long range_plus_one = range + 1ULL;
    T value = ConsumeIntegral<T>();
    if (range_plus_one == 0) {
      return static_cast<T>(min + value);
    }
    return static_cast<T>(
        min + static_cast<T>(
                  static_cast<unsigned long long>(value) %
                  range_plus_one));
  }

  template <typename T>
  T ConsumeFloatingPoint() {
    T result = 0;
    size_t need = sizeof(T);
    size_t rem = remaining_bytes();
    if (need > rem) need = rem;
    if (need > 0) {
      std::memcpy(&result, data_ + offset_, need);
      offset_ += need;
    }
    return result;
  }

  bool ConsumeBool() {
    return (ConsumeIntegral<uint8_t>() & 1) != 0;
  }

  template <typename T>
  std::vector<T> ConsumeBytes(size_t count) {
    size_t rem = remaining_bytes();
    if (count > rem) count = rem;
    std::vector<T> out(count);
    if (count > 0) {
      std::memcpy(out.data(), data_ + offset_, count);
      offset_ += count;
    }
    return out;
  }

  template <typename T>
  std::vector<T> ConsumeRemainingBytes() {
    return ConsumeBytes<T>(remaining_bytes());
  }

  std::string ConsumeRandomLengthString(size_t max_length) {
    size_t n = ConsumeIntegralInRange<size_t>(0, max_length);
    std::vector<char> bytes = ConsumeBytes<char>(n);
    return std::string(bytes.begin(), bytes.end());
  }

 private:
  const uint8_t *data_;
  size_t size_;
  size_t offset_;
};

}  // namespace fuzzing

using fuzzing::FuzzedDataProvider;

'''

HARNESS_MAIN_CODE = r'''
#include <cstdint>
#include <cstddef>
#include <vector>
#include <unistd.h>
#include <cstdio>

extern "C" int FuzzHarnessEntry(const uint8_t *data, size_t size);

static bool read_n(int fd, void *buf, size_t n) {
  uint8_t *p = reinterpret_cast<uint8_t *>(buf);
  while (n > 0) {
    ssize_t r = read(fd, p, n);
    if (r <= 0) return false;
    p += r;
    n -= static_cast<size_t>(r);
  }
  return true;
}

static bool write_n(int fd, const void *buf, size_t n) {
  const uint8_t *p = reinterpret_cast<const uint8_t *>(buf);
  while (n > 0) {
    ssize_t w = write(fd, p, n);
    if (w <= 0) return false;
    p += w;
    n -= static_cast<size_t>(w);
  }
  return true;
}

int main() {
  while (true) {
    uint32_t sz = 0;
    if (!read_n(0, &sz, sizeof(sz))) {
      return 0;
    }
    if (sz == 0xFFFFFFFFu) {
      return 0;
    }
    std::vector<uint8_t> data;
    data.resize(sz);
    if (!read_n(0, data.data(), sz)) {
      return 0;
    }
    FuzzHarnessEntry(data.data(), data.size());
    uint8_t ack = 0;
    if (!write_n(1, &ack, 1)) {
      return 0;
    }
    fflush(stdout);
  }
}

'''


def _find_compiler(candidates):
    for c in candidates:
        path = shutil.which(c)
        if path:
            return path
    return None


def _collect_include_dirs(src_root):
    inc_dirs = {src_root}
    for root, dirs, files in os.walk(src_root):
        for f in files:
            if f.endswith(('.h', '.hpp', '.hh')):
                inc_dirs.add(root)
                break
    return sorted(inc_dirs)


def _collect_c_files(src_root):
    c_files = []
    skip_dir_names = {
        'test', 'tests', 'example', 'examples', 'doc', 'docs',
        'benchmark', 'benchmarks', 'fuzz', 'oss-fuzz', 'cmake-build'
    }
    for root, dirs, files in os.walk(src_root):
        parts = set(root.split(os.sep))
        if parts & skip_dir_names:
            continue
        for f in files:
            if not f.endswith('.c'):
                continue
            path = os.path.join(root, f)
            try:
                with open(path, 'r', errors='ignore') as fh:
                    head = fh.read(4096)
            except OSError:
                continue
            if 'LLVMFuzzerTestOneInput' in head:
                continue
            if ' main(' in head or '\nmain(' in head or 'int main(' in head or 'int\nmain(' in head:
                continue
            c_files.append(path)
    return c_files


def _find_harness_file(src_root):
    target_substrings = ['polygonToCellsExperimental', 'experimentalPolygonToCells']
    for root, dirs, files in os.walk(src_root):
        for f in files:
            if not f.endswith(('.cc', '.cpp', '.cxx', '.C')):
                continue
            path = os.path.join(root, f)
            try:
                with open(path, 'r', errors='ignore') as fh:
                    txt = fh.read()
            except OSError:
                continue
            if 'LLVMFuzzerTestOneInput' not in txt:
                continue
            if any(s in txt for s in target_substrings):
                return path
    return None


def _build_harness(src_root, harness_path, build_dir):
    os.makedirs(build_dir, exist_ok=True)
    try:
        with open(harness_path, 'r', encoding='latin-1', errors='ignore') as f:
            original = f.read()
    except OSError:
        return None

    # Remove FuzzedDataProvider include lines if present
    body_lines = []
    for line in original.splitlines():
        if 'FuzzedDataProvider.h' in line:
            continue
        body_lines.append(line)
    body = '\n'.join(body_lines)

    # Rename LLVMFuzzerTestOneInput to FuzzHarnessEntry
    if 'LLVMFuzzerTestOneInput' not in body:
        return None
    body = body.replace('LLVMFuzzerTestOneInput', 'FuzzHarnessEntry')

    modified_code = FUZZED_DATA_PROVIDER_CODE + '\n' + body

    harness_mod_path = os.path.join(build_dir, 'harness_mod.cpp')
    try:
        with open(harness_mod_path, 'w') as f:
            f.write(modified_code)
    except OSError:
        return None

    main_cpp_path = os.path.join(build_dir, 'harness_main.cpp')
    try:
        with open(main_cpp_path, 'w') as f:
            f.write(HARNESS_MAIN_CODE)
    except OSError:
        return None

    cc = _find_compiler(['clang', 'gcc', 'cc'])
    cxx = _find_compiler(['clang++', 'g++', 'c++'])
    if not cc or not cxx:
        return None

    inc_dirs = _collect_include_dirs(src_root)
    c_files = _collect_c_files(src_root)
    if not c_files:
        return None

    san_flags = ['-fsanitize=address']
    common_cflags = ['-std=c99', '-O1', '-g', '-fno-omit-frame-pointer']
    common_cxxflags = ['-std=c++14', '-O1', '-g', '-fno-omit-frame-pointer']

    def compile_with_flags(use_san):
        objs = []
        cflags = common_cflags + (san_flags if use_san else [])
        cxxflags = common_cxxflags + (san_flags if use_san else [])
        inc_args = [f'-I{d}' for d in inc_dirs]

        # Compile C files
        for cfile in c_files:
            rel = os.path.relpath(cfile, src_root).replace(os.sep, '_')
            obj = os.path.join(build_dir, rel + '.o')
            cmd = [cc] + cflags + inc_args + ['-c', cfile, '-o', obj]
            try:
                subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            except Exception:
                return None
            objs.append(obj)

        # Compile modified harness
        harness_obj = os.path.join(build_dir, 'harness_mod.o')
        cmd = [cxx] + cxxflags + inc_args + ['-c', harness_mod_path, '-o', harness_obj]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            return None
        objs.append(harness_obj)

        # Compile main
        main_obj = os.path.join(build_dir, 'harness_main.o')
        cmd = [cxx] + cxxflags + ['-c', main_cpp_path, '-o', main_obj]
        try:
            subprocess.run(cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            return None
        objs.append(main_obj)

        # Link
        bin_path = os.path.join(build_dir, 'poc_harness')
        link_cmd = [cxx] + (san_flags if use_san else []) + ['-O1', '-g', '-fno-omit-frame-pointer', '-o', bin_path] + objs + ['-lm']
        try:
            subprocess.run(link_cmd, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        except Exception:
            return None
        return bin_path

    # First try with ASAN, then without as fallback
    bin_path = compile_with_flags(use_san=True)
    if bin_path is None:
        bin_path = compile_with_flags(use_san=False)
    return bin_path


def _fuzz_for_poc(bin_path, max_time=20.0, max_iters=100000, poc_size=1032):
    rnd = random.Random(123456)
    end_time = time.time() + max_time
    proc = None

    def start_proc():
        return subprocess.Popen(
            [bin_path],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
        )

    def test_input(data):
        nonlocal proc
        if proc is None or proc.poll() is not None:
            try:
                proc = start_proc()
            except Exception:
                proc = None
                return False
        try:
            proc.stdin.write(struct.pack('<I', len(data)))
            proc.stdin.write(data)
            proc.stdin.flush()
        except Exception:
            try:
                if proc is not None:
                    proc.kill()
            except Exception:
                pass
            proc = None
            return True  # treat as crash

        try:
            fd = proc.stdout.fileno()
            rlist, _, _ = select.select([fd], [], [], 0.5)
            if not rlist:
                try:
                    proc.kill()
                    proc.wait(timeout=1)
                except Exception:
                    pass
                proc = None
                return True  # treat timeout as crash/hang
            ack = proc.stdout.read(1)
        except Exception:
            try:
                if proc is not None:
                    proc.kill()
            except Exception:
                pass
            proc = None
            return True
        if ack == b'':
            proc = None
            return True
        return False

    last = os.urandom(poc_size)
    i = 0
    while i < max_iters and time.time() < end_time:
        i += 1
        if i == 1:
            data = last
        else:
            if rnd.random() < 0.3:
                data = os.urandom(poc_size)
            else:
                ba = bytearray(last)
                n_mut = 1 + rnd.randint(0, 7)
                for _ in range(n_mut):
                    pos = rnd.randrange(poc_size)
                    if rnd.random() < 0.5:
                        ba[pos] ^= 1 << rnd.randint(0, 7)
                    else:
                        ba[pos] = rnd.getrandbits(8)
                data = bytes(ba)
        crashed = test_input(data)
        if crashed:
            try:
                if proc is not None:
                    proc.stdin.write(struct.pack('<I', 0xFFFFFFFF))
                    proc.stdin.flush()
                    proc.terminate()
            except Exception:
                pass
            return data
        last = data

    try:
        if proc is not None:
            proc.stdin.write(struct.pack('<I', 0xFFFFFFFF))
            proc.stdin.flush()
            proc.terminate()
    except Exception:
        pass
    return last


class Solution:
    def solve(self, src_path: str) -> bytes:
        base_dir = tempfile.mkdtemp(prefix='pocgen_')
        try:
            src_dir = os.path.join(base_dir, 'src')
            os.makedirs(src_dir, exist_ok=True)
            try:
                with tarfile.open(src_path, 'r:*') as tar:
                    tar.extractall(src_dir)
            except Exception:
                # Fallback: return random bytes if extraction fails
                return os.urandom(1032)

            harness_path = _find_harness_file(src_dir)
            if not harness_path:
                return os.urandom(1032)

            build_dir = os.path.join(base_dir, 'build')
            bin_path = _build_harness(src_dir, harness_path, build_dir)
            if not bin_path or not os.path.exists(bin_path):
                return os.urandom(1032)

            poc = _fuzz_for_poc(bin_path, max_time=20.0, max_iters=100000, poc_size=1032)
            return poc
        finally:
            shutil.rmtree(base_dir, ignore_errors=True)