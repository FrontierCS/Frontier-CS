import os
import re
import tarfile
import tempfile
from typing import Dict, List, Optional, Set, Tuple


class Solution:
    def _is_dir(self, p: str) -> bool:
        try:
            return os.path.isdir(p)
        except Exception:
            return False

    def _ensure_src_dir(self, src_path: str) -> Tuple[str, Optional[tempfile.TemporaryDirectory]]:
        if self._is_dir(src_path):
            return src_path, None
        td = tempfile.TemporaryDirectory()
        root = td.name
        try:
            with tarfile.open(src_path, "r:*") as tf:
                def is_within_directory(directory: str, target: str) -> bool:
                    abs_directory = os.path.abspath(directory)
                    abs_target = os.path.abspath(target)
                    return os.path.commonprefix([abs_directory, abs_target]) == abs_directory

                for m in tf.getmembers():
                    if not m.name:
                        continue
                    dest = os.path.join(root, m.name)
                    if not is_within_directory(root, dest):
                        continue
                tf.extractall(root)
        except Exception:
            # If not a tarball, treat as directory path anyway
            return src_path, td
        # Some tarballs have a single top directory
        try:
            entries = [e for e in os.listdir(root) if e not in (".", "..")]
            if len(entries) == 1:
                one = os.path.join(root, entries[0])
                if os.path.isdir(one):
                    return one, td
        except Exception:
            pass
        return root, td

    def _iter_source_files(self, root: str) -> List[str]:
        exts = {".c", ".cc", ".cpp", ".cxx", ".h", ".hh", ".hpp", ".hxx"}
        out = []
        for dirpath, _, filenames in os.walk(root):
            for fn in filenames:
                _, ext = os.path.splitext(fn)
                if ext.lower() in exts:
                    out.append(os.path.join(dirpath, fn))
        return out

    def _read_text(self, path: str, limit: int = 2_000_000) -> str:
        try:
            with open(path, "rb") as f:
                data = f.read(limit)
            return data.decode("utf-8", errors="ignore")
        except Exception:
            return ""

    def _parse_int(self, s: str) -> Optional[int]:
        s = s.strip()
        if not s:
            return None
        try:
            return int(s, 0)
        except Exception:
            return None

    def _find_macro_define(self, root: str, name: str) -> Optional[int]:
        pat = re.compile(r"^\s*#\s*define\s+" + re.escape(name) + r"\s+([0-9]+|0x[0-9A-Fa-f]+)\b", re.M)
        for path in self._iter_source_files(root):
            txt = self._read_text(path)
            if name not in txt:
                continue
            m = pat.search(txt)
            if m:
                return self._parse_int(m.group(1))
        return None

    def _find_enum_assign(self, root: str, name: str) -> Optional[int]:
        pat = re.compile(r"\b" + re.escape(name) + r"\b\s*=\s*([0-9]+|0x[0-9A-Fa-f]+)\b")
        for path in self._iter_source_files(root):
            txt = self._read_text(path)
            if name not in txt:
                continue
            m = pat.search(txt)
            if m:
                return self._parse_int(m.group(1))
        return None

    def _find_symbol_any(self, root: str, name: str) -> Optional[int]:
        v = self._find_macro_define(root, name)
        if v is not None:
            return v
        return self._find_enum_assign(root, name)

    def _select_fuzzer_file(self, root: str) -> Optional[str]:
        best = None
        best_score = -1
        keys = [
            "LLVMFuzzerTestOneInput",
            "otDataset",
            "OperationalDataset",
            "Dataset",
            "IsTlvValid",
            "ActiveTimestamp",
            "PendingTimestamp",
            "DelayTimer",
            "otOperationalDatasetTlvs",
            "otDatasetSetActiveTlvs",
            "otDatasetSetPendingTlvs",
            "MeshCoP",
        ]
        for path in self._iter_source_files(root):
            txt = self._read_text(path, limit=1_000_000)
            if "LLVMFuzzerTestOneInput" not in txt:
                continue
            score = 0
            for k in keys:
                if k in txt:
                    score += 3 if k in ("otDatasetSetActiveTlvs", "otDatasetSetPendingTlvs", "IsTlvValid") else 1
            if score > best_score:
                best_score = score
                best = path
        return best

    def _find_is_tlv_valid_file(self, root: str) -> Optional[str]:
        needles = ["IsTlvValid", "Dataset::IsTlvValid"]
        for path in self._iter_source_files(root):
            txt = self._read_text(path, limit=1_500_000)
            if any(n in txt for n in needles):
                # Heuristic: prefer .cpp/.cc
                _, ext = os.path.splitext(path.lower())
                if ext in (".cpp", ".cc", ".cxx"):
                    return path
        # fallback: any file
        for path in self._iter_source_files(root):
            txt = self._read_text(path, limit=1_500_000)
            if any(n in txt for n in needles):
                return path
        return None

    def _unknown_tlv_allowed(self, root: str) -> Optional[bool]:
        path = self._find_is_tlv_valid_file(root)
        if not path:
            return None
        txt = self._read_text(path, limit=2_000_000)
        if "IsTlvValid" not in txt:
            return None

        # Try to isolate the function body roughly
        idx = txt.find("IsTlvValid")
        if idx == -1:
            return None
        snippet = txt[idx: idx + 12000]

        dpos = snippet.find("default")
        if dpos == -1:
            # no default => likely rejects unknown or handles all; can't tell
            return None
        after = snippet[dpos: dpos + 400].lower()

        # If default explicitly makes it false or exits, unknown rejected
        reject_markers = [
            "return false",
            "isvalid = false",
            "is_valid = false",
            "exitnow(false",
            "verifyorexit(false",
            "ot_exit_now",
            "exit now",
        ]
        for m in reject_markers:
            if m in after:
                return False

        # If default just breaks or does nothing, unknown likely allowed
        allow_markers = ["break", ";"]
        for m in allow_markers:
            if m in after:
                return True
        return None

    def _collect_known_tlv_types(self, root: str) -> Set[int]:
        known: Set[int] = set()
        # Attempt to find an enum listing TLV types
        candidates = []
        for path in self._iter_source_files(root):
            base = os.path.basename(path).lower()
            if "tlv" in base and ("meshcop" in base or "dataset" in base or "mle" in base):
                candidates.append(path)
        # Add files likely containing TLV enums
        candidates = candidates[:80] + [p for p in self._iter_source_files(root) if p not in candidates][:20]

        enum_assign_pat = re.compile(r"\b(k[A-Za-z0-9_]*Timestamp|kDelayTimer|kNetworkName|kChannelMask|kNetworkKey|kPskc|kExtendedPanId|kPanId|kMeshLocalPrefix|kSecurityPolicy|kChannel)\b\s*=\s*([0-9]+|0x[0-9A-Fa-f]+)\b")
        any_assign_pat = re.compile(r"\b(k[A-Za-z0-9_]+)\b\s*=\s*([0-9]+|0x[0-9A-Fa-f]+)\b")

        for path in candidates:
            txt = self._read_text(path, limit=1_500_000)
            if "enum" not in txt and "kType" not in txt and "kActiveTimestamp" not in txt:
                continue
            for m in enum_assign_pat.finditer(txt):
                v = self._parse_int(m.group(2))
                if v is not None and 0 <= v <= 255:
                    known.add(v)
            # If we got too few, broaden
            if len(known) < 10 and ("Tlv" in txt or "TLV" in txt):
                for m in any_assign_pat.finditer(txt):
                    v = self._parse_int(m.group(2))
                    if v is not None and 0 <= v <= 255:
                        known.add(v)
            if len(known) >= 60:
                break
        return known

    def _choose_unused_type(self, known: Set[int]) -> int:
        # Prefer vendor/reserved range to avoid clashes
        for t in range(0x80, 0x100):
            if t not in known:
                return t
        for t in range(0, 0x80):
            if t not in known:
                return t
        return 0xFF

    def _infer_prefix_from_fuzzer(self, fuzzer_txt: str, max_len: int) -> Tuple[bytes, int]:
        # Return (prefix_bytes, bytes_consumed_before_tlvs)
        if "FuzzedDataProvider" not in fuzzer_txt:
            return b"", 0

        # Look for ConsumeIntegralInRange<type>(0, OT_OPERATIONAL_DATASET_MAX_LENGTH) used as length
        m = re.search(
            r"ConsumeIntegralInRange\s*<\s*([A-Za-z0-9_:]+)\s*>\s*\(\s*([^\),]+)\s*,\s*([^\)]+)\)",
            fuzzer_txt,
        )
        if not m:
            return b"", 0

        tname = m.group(1).strip()
        min_expr = m.group(2).strip()
        max_expr = m.group(3).strip()

        def eval_bound(expr: str) -> Optional[int]:
            expr = expr.strip()
            expr = re.sub(r"\s+", "", expr)
            if expr == "OT_OPERATIONAL_DATASET_MAX_LENGTH":
                return max_len
            if expr == "OT_OPERATIONAL_DATASET_MAX_LENGTH-1":
                return max_len - 1
            if expr == "sizeof(dataset.mTlvs)-1" or expr == "sizeof(dataset.mTlvs)-1u":
                return max_len - 1
            if expr == "sizeof(dataset.mTlvs)" or expr == "sizeof(dataset.mTlvs)":
                return max_len
            if expr.isdigit() or expr.lower().startswith("0x"):
                return self._parse_int(expr)
            return None

        min_v = eval_bound(min_expr)
        max_v = eval_bound(max_expr)
        if min_v is None:
            min_v = 0
        if max_v is None:
            max_v = max_len

        target = max_v
        remainder = target - min_v
        if remainder < 0:
            remainder = 0

        # Encode the consumed integral so that value % (range) == remainder
        # Most implementations consume integral in native endianness; assume little-endian.
        if tname.endswith("size_t") or tname == "size_t":
            n = (8 if (8 == (8 if True else 8)) else 8)
            prefix = int(remainder).to_bytes(n, "little", signed=False)
            return prefix, n
        if tname.endswith("uint8_t") or tname == "uint8_t" or tname.endswith("unsignedchar"):
            n = 1
            prefix = bytes([remainder & 0xFF])
            return prefix, n
        if tname.endswith("uint16_t") or tname == "uint16_t":
            n = 2
            prefix = int(remainder & 0xFFFF).to_bytes(n, "little", signed=False)
            return prefix, n
        if tname.endswith("uint32_t") or tname == "uint32_t":
            n = 4
            prefix = int(remainder & 0xFFFFFFFF).to_bytes(n, "little", signed=False)
            return prefix, n
        # Default: assume size_t
        n = 8
        prefix = int(remainder).to_bytes(n, "little", signed=False)
        return prefix, n

    def _build_tlvs(self, total_len: int, active_ts_type: int, network_name_type: Optional[int], unknown_allowed: bool, known_types: Set[int]) -> bytes:
        if total_len < 4:
            return bytes([active_ts_type, 0])

        final = bytes([active_ts_type & 0xFF, 0x00])
        pad_total = total_len - len(final)

        # Prefer single unknown padding TLV if unknown allowed (and helps if duplicates are rejected elsewhere)
        if unknown_allowed and pad_total >= 2:
            pad_type = self._choose_unused_type(known_types | {active_ts_type & 0xFF})
            pad_len = pad_total - 2
            if 0 <= pad_len <= 255:
                return bytes([pad_type & 0xFF, pad_len & 0xFF]) + (b"\x00" * pad_len) + final

        # Otherwise, try to pad with repeated NetworkName TLVs (len up to 16)
        if network_name_type is not None:
            out = bytearray()
            remaining = pad_total
            # ensure we can always complete remaining exactly with final TLV stream
            while remaining > 0:
                if remaining < 3:
                    break
                l = min(16, remaining - 2)
                if l < 1:
                    break
                out.append(network_name_type & 0xFF)
                out.append(l & 0xFF)
                out.extend(b"A" * l)
                remaining -= (2 + l)
            if remaining == 0:
                out.extend(final)
                return bytes(out)

        # Fallback: single padding TLV with some type (even if unknown disallowed, try anyway)
        pad_type = self._choose_unused_type(known_types | {active_ts_type & 0xFF})
        pad_len = pad_total - 2
        if pad_total >= 2 and 0 <= pad_len <= 255:
            return bytes([pad_type & 0xFF, pad_len & 0xFF]) + (b"\x00" * pad_len) + final

        # Last resort: just final
        return final

    def solve(self, src_path: str) -> bytes:
        root, td = self._ensure_src_dir(src_path)
        try:
            max_len = self._find_symbol_any(root, "OT_OPERATIONAL_DATASET_MAX_LENGTH")
            if max_len is None or max_len <= 0 or max_len > 2048:
                max_len = 254

            active_ts = self._find_symbol_any(root, "kActiveTimestamp")
            if active_ts is None:
                active_ts = self._find_symbol_any(root, "OT_MESHCOP_TLV_ACTIVE_TIMESTAMP")
            if active_ts is None:
                active_ts = 9  # common in some implementations

            net_name = self._find_symbol_any(root, "kNetworkName")
            if net_name is None:
                net_name = self._find_symbol_any(root, "OT_MESHCOP_TLV_NETWORK_NAME")

            unknown_allowed = self._unknown_tlv_allowed(root)
            if unknown_allowed is None:
                unknown_allowed = True

            known_types = self._collect_known_tlv_types(root)

            fuzzer_path = self._select_fuzzer_file(root)
            prefix = b""
            if fuzzer_path:
                ftxt = self._read_text(fuzzer_path, limit=2_000_000)
                prefix, _ = self._infer_prefix_from_fuzzer(ftxt, max_len)

            tlvs = self._build_tlvs(max_len, active_ts, net_name, bool(unknown_allowed), known_types)

            return prefix + tlvs
        finally:
            if td is not None:
                td.cleanup()