import os
import tarfile
import tempfile
import shutil
import subprocess
import glob
import stat
import random


class Solution:
    def solve(self, src_path: str) -> bytes:
        def extract_tarball(tar_path: str, target_dir: str) -> None:
            with tarfile.open(tar_path, 'r:*') as tar:
                def is_within_directory(directory: str, target: str) -> bool:
                    abs_directory = os.path.abspath(directory)
                    abs_target = os.path.abspath(target)
                    return os.path.commonprefix([abs_directory, abs_target]) == abs_directory

                for member in tar.getmembers():
                    member_path = os.path.join(target_dir, member.name)
                    if not is_within_directory(target_dir, member_path):
                        continue
                    tar.extract(member, target_dir)

        def find_root(base_dir: str) -> str:
            try:
                entries = [e for e in os.listdir(base_dir) if not e.startswith('.') and not e.endswith('.log')]
            except FileNotFoundError:
                return base_dir
            if len(entries) == 1:
                only = os.path.join(base_dir, entries[0])
                if os.path.isdir(only):
                    return only
            return base_dir

        def build_project(root: str):
            env = os.environ.copy()
            cc = shutil.which('clang') or shutil.which('gcc') or 'gcc'
            cxx = shutil.which('clang++') or shutil.which('g++') or 'g++'
            env.setdefault('CC', cc)
            env.setdefault('CXX', cxx)

            def add_flag(var: str, flag: str) -> None:
                val = env.get(var, '')
                if flag not in val:
                    val = (val + ' ' + flag).strip()
                env[var] = val

            # Add reasonable ASan/debug flags
            for v in ('CFLAGS', 'CXXFLAGS'):
                add_flag(v, '-g')
                add_flag(v, '-O1')
                add_flag(v, '-fno-omit-frame-pointer')
                add_flag(v, '-fsanitize=address')

            env.setdefault('FUZZING_ENGINE', 'libfuzzer')
            env.setdefault('SANITIZER', 'address')
            env.setdefault('ARCHITECTURE', 'x86_64')

            if 'clang' in os.path.basename(cc):
                env['LIB_FUZZING_ENGINE'] = '-fsanitize=fuzzer,address'
            else:
                env.setdefault('LIB_FUZZING_ENGINE', '')

            out_dir = os.path.join(root, 'out')
            os.makedirs(out_dir, exist_ok=True)
            env.setdefault('OUT', out_dir)

            build_ok = False

            # Try build.sh-style script
            for name in ('build.sh', 'build.bash', 'Build.sh'):
                script = os.path.join(root, name)
                if os.path.isfile(script):
                    try:
                        res = subprocess.run(
                            ['bash', script],
                            cwd=root,
                            env=env,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            timeout=300,
                        )
                        if res.returncode == 0:
                            build_ok = True
                            break
                    except Exception:
                        pass

            # Try CMake-based build
            if not build_ok and os.path.exists(os.path.join(root, 'CMakeLists.txt')):
                bdir = os.path.join(root, 'build')
                os.makedirs(bdir, exist_ok=True)
                try:
                    res = subprocess.run(
                        ['cmake', '..'],
                        cwd=bdir,
                        env=env,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=120,
                    )
                    if res.returncode == 0:
                        res = subprocess.run(
                            ['make', '-j4'],
                            cwd=bdir,
                            env=env,
                            stdout=subprocess.DEVNULL,
                            stderr=subprocess.DEVNULL,
                            timeout=300,
                        )
                        if res.returncode == 0:
                            build_ok = True
                except Exception:
                    pass

            # Try plain make
            if not build_ok and os.path.exists(os.path.join(root, 'Makefile')):
                try:
                    res = subprocess.run(
                        ['make', '-j4'],
                        cwd=root,
                        env=env,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=300,
                    )
                    if res.returncode == 0:
                        build_ok = True
                except Exception:
                    pass

            return build_ok, env

        def is_elf_executable(path: str) -> bool:
            try:
                st = os.stat(path)
            except OSError:
                return False
            if not stat.S_ISREG(st.st_mode):
                return False
            if not (st.st_mode & (stat.S_IXUSR | stat.S_IXGRP | stat.S_IXOTH)):
                return False
            try:
                with open(path, 'rb') as f:
                    magic = f.read(4)
                return magic == b'\x7fELF'
            except OSError:
                return False

        def find_executables(root: str):
            exes = []
            for dirpath, _, filenames in os.walk(root):
                for name in filenames:
                    full = os.path.join(dirpath, name)
                    if is_elf_executable(full):
                        if '.so' in name or name.endswith('.a'):
                            continue
                        exes.append(full)
            return exes

        def is_libfuzzer_exe(path: str) -> bool:
            try:
                with open(path, 'rb') as f:
                    data = f.read()
                if b'LLVMFuzzerTestOneInput' in data:
                    return True
                if b'libFuzzer' in data or b'LibFuzzer' in data:
                    return True
            except Exception:
                pass
            return False

        def run_libfuzzer_for_crash(exe: str, env) -> bytes | None:
            exe_dir = os.path.dirname(exe) or '.'
            artifact_dir = os.path.join(exe_dir, 'artifacts_' + os.path.basename(exe))
            os.makedirs(artifact_dir, exist_ok=True)
            cmd = [
                exe,
                '-max_total_time=60',
                '-timeout=10',
                '-rss_limit_mb=12000',
                '-detect_leaks=0',
                f'-artifact_prefix={artifact_dir}/',
            ]
            try:
                subprocess.run(
                    cmd,
                    cwd=exe_dir,
                    env=env,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=75,
                )
            except subprocess.TimeoutExpired:
                pass
            except Exception:
                return None

            crash_files = []
            for pattern in ('crash-*', 'leak-*', 'timeout-*', 'oom-*'):
                crash_files.extend(glob.glob(os.path.join(artifact_dir, pattern)))
            if not crash_files:
                return None
            crash_files.sort(key=lambda p: os.path.getsize(p))
            try:
                with open(crash_files[0], 'rb') as f:
                    return f.read()
            except Exception:
                return None

        def random_stdin_fuzz(exe: str, env, trials: int = 128) -> bytes | None:
            exe_dir = os.path.dirname(exe) or '.'
            for _ in range(trials):
                length = random.randint(1, 256)
                data = os.urandom(length)
                try:
                    res = subprocess.run(
                        [exe],
                        cwd=exe_dir,
                        env=env,
                        input=data,
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        timeout=2,
                    )
                    if res.returncode != 0:
                        return data
                except Exception:
                    continue
            return None

        with tempfile.TemporaryDirectory() as tmpdir:
            extract_tarball(src_path, tmpdir)
            root = find_root(tmpdir)
            build_project(root)  # even if build fails, there may be prebuilt binaries
            _, env = build_project(root)

            exes = find_executables(root)
            if not exes:
                return b'A'

            def exe_key(path: str):
                name = os.path.basename(path).lower()
                score = 0
                if 'fuzz' not in name:
                    score += 2
                if 'h225' not in name and 'ras' not in name:
                    score += 1
                if os.sep + 'out' + os.sep not in path:
                    score += 1
                return score, len(path)

            exes.sort(key=exe_key)

            for exe in exes:
                if is_libfuzzer_exe(exe):
                    data = run_libfuzzer_for_crash(exe, env)
                    if data:
                        return data

            for exe in exes[:3]:
                data = random_stdin_fuzz(exe, env)
                if data:
                    return data

            return b'A'