import os
import re
import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        bsf_index = 0
        pkt_min_size = 64
        media_src = None
        harness_src = None

        with tarfile.open(src_path, "r:*") as tar:
            bsf_index = self._find_bsf_index(tar)
            if bsf_index is None:
                bsf_index = 0

            media_src = self._find_media_source(tar)
            if media_src is not None:
                pkt_min_size = self._infer_min_pkt_size(media_src)

            harness_src = self._find_harness_source(tar)

        # Heuristic: how many initial bytes are consumed before pkt->data
        header_offset = self._infer_header_offset(harness_src)

        # Target payload size: large enough for typical parsing plus padding
        payload_size = max(1024, pkt_min_size)

        total_size = header_offset + payload_size
        if total_size < header_offset + 1:
            total_size = header_offset + 1

        buf = bytearray(total_size)

        # Initialize buffer with deterministic pattern (non-zero to avoid accidental magic zeros)
        for i in range(total_size):
            buf[i] = (31 * i + 17) & 0xFF

        # Put BSF index into all bytes that might be used as selector before pkt->data,
        # so whichever byte the harness uses as index will likely select our target BSF.
        for i in range(min(header_offset, total_size)):
            buf[i] = bsf_index & 0xFF
        if header_offset == 0 and total_size > 0:
            buf[0] = bsf_index & 0xFF

        # Apply simple header constraints for media100_to_mjpegb relative to pkt->data
        if media_src is not None:
            self._apply_header_constraints(media_src, buf, header_offset)

        return bytes(buf)

    def _find_media_source(self, tar: tarfile.TarFile) -> str | None:
        # Prefer direct filename match
        for m in tar.getmembers():
            if not m.isfile():
                continue
            base = os.path.basename(m.name)
            if base == "media100_to_mjpegb.c":
                f = tar.extractfile(m)
                if not f:
                    continue
                data = f.read()
                return data.decode("latin1", errors="ignore")

        # Fallback: search any C file containing the identifier
        target = b"media100_to_mjpegb"
        for m in tar.getmembers():
            if not m.isfile():
                continue
            base = os.path.basename(m.name)
            if not base.endswith(".c"):
                continue
            f = tar.extractfile(m)
            if not f:
                continue
            data = f.read()
            if target in data:
                return data.decode("latin1", errors="ignore")

        return None

    def _infer_min_pkt_size(self, media_src: str) -> int:
        # Look for conditions like "pkt->size < N" or "pkt->size <= N"
        sizes = []
        for m in re.finditer(r"pkt->size\s*(?:<|<=)\s*(\d+)", media_src):
            try:
                sizes.append(int(m.group(1)))
            except ValueError:
                continue
        if sizes:
            # Need strictly greater than the maximum "<=" or "<" constant
            return max(sizes) + 1
        return 64

    def _find_harness_source(self, tar: tarfile.TarFile) -> str | None:
        # Find the BSF fuzzer source: it will contain LLVMFuzzerTestOneInput and AVBitStreamFilter
        for m in tar.getmembers():
            if not m.isfile():
                continue
            base = os.path.basename(m.name)
            if not (base.endswith(".c") or base.endswith(".cc") or base.endswith(".cpp") or base.endswith(".cxx")):
                continue
            f = tar.extractfile(m)
            if not f:
                continue
            data = f.read()
            if b"LLVMFuzzerTestOneInput" in data and b"AVBitStreamFilter" in data:
                return data.decode("latin1", errors="ignore")
        return None

    def _infer_header_offset(self, harness_src: str | None) -> int:
        # Default assumption from common ffmpeg BSF fuzzer design and ground-truth length
        if not harness_src:
            return 1

        # Try to detect pkt.data = data + N; or pkt.data = data;
        m = re.search(
            r"pkt(?:_in)?\.data\s*=\s*(?:\(\s*uint8_t\s*\*\s*\)\s*)?(?P<expr>[^;]+);",
            harness_src,
        )
        if m:
            expr = m.group("expr")
            m2 = re.search(r"\bdata\s*\+\s*(\d+)", expr)
            if m2:
                try:
                    return int(m2.group(1))
                except ValueError:
                    pass
            elif re.search(r"\bdata\b", expr):
                return 0

        # Fallback heuristic
        return 1

    def _find_bsf_index(self, tar: tarfile.TarFile) -> int | None:
        # 1) Try to locate explicit list of BSF names in harness (if present)
        harness_src = self._find_harness_source(tar)
        if harness_src:
            idx = self._find_bsf_index_in_harness_names(harness_src)
            if idx is not None:
                return idx

        # 2) Fallback: parse libavcodec BSF list (ff_media100_to_mjpegb_bsf order)
        idx = self._find_bsf_index_via_bsf_list(tar)
        if idx is not None:
            return idx

        return None

    def _find_bsf_index_in_harness_names(self, harness_src: str) -> int | None:
        # Look for an array initializer that includes "media100_to_mjpegb"
        # e.g., static const char *const bsf_names[] = { "null", ..., "media100_to_mjpegb", ... };
        matches = list(
            re.finditer(
                r"static\s+const\s+char[^=]*=\s*{[^}]*\"media100_to_mjpegb\"[^}]*}",
                harness_src,
                re.DOTALL,
            )
        )
        for m in matches:
            array_text = m.group(0)
            names = re.findall(r"\"([^\"]+)\"", array_text)
            try:
                pos = names.index("media100_to_mjpegb")
                return pos
            except ValueError:
                continue
        return None

    def _find_bsf_index_via_bsf_list(self, tar: tarfile.TarFile) -> int | None:
        target_symbol = "ff_media100_to_mjpegb_bsf"
        target_bytes = target_symbol.encode("ascii")

        for m in tar.getmembers():
            if not m.isfile():
                continue
            base = os.path.basename(m.name)
            if not base.endswith(".c"):
                continue
            f = tar.extractfile(m)
            if not f:
                continue
            data = f.read()
            if target_bytes not in data:
                continue
            text = data.decode("latin1", errors="ignore")

            # Prefer static const AVBitStreamFilter * const ... = { ... ff_media100_to_mjpegb_bsf ... };
            arr_match = re.search(
                r"static\s+const\s+AVBitStreamFilter\s*\*\s*const\s+\w+\s*\[\s*\]\s*=\s*{[^}]*ff_media100_to_mjpegb_bsf[^}]*}",
                text,
                re.DOTALL,
            )
            if arr_match:
                arr_text = arr_match.group(0)
            else:
                # Fallback: take the nearest {...} around the symbol
                pos = text.find(target_symbol)
                if pos == -1:
                    continue
                brace_start = text.rfind("{", 0, pos)
                brace_end = text.find("}", pos)
                if brace_start == -1 or brace_end == -1:
                    continue
                arr_text = text[brace_start:brace_end]

            entries = re.findall(r"&ff_([A-Za-z0-9_]+)_bsf", arr_text)
            try:
                idx = entries.index("media100_to_mjpegb")
                return idx
            except ValueError:
                continue

        return None

    def _apply_header_constraints(self, media_src: str, buf: bytearray, pkt_offset: int) -> None:
        # Apply very simple constraints inferred from patterns like:
        # if (pkt->size < N) return AVERROR...; (handled earlier)
        # if (AV_RB32(pkt->data + off) != MKTAG('a','b','c','d')) return AVERROR...;
        # if (pkt->data[idx] != value) return AVERROR...;
        # Only handle the direct AVERROR_INVALIDDATA style to avoid mis-interpreting code.
        import math

        if not media_src:
            return

        total_len = len(buf)
        payload_len = max(0, total_len - pkt_offset)

        # MKTAG-based checks
        pattern_mktag = re.compile(
            r"if\s*\(\s*AV_R[BL]\d+\s*\(\s*pkt->data(?P<offset>(?:\s*[\+\-]\s*\d+)?)\s*\)\s*!=\s*MKTAG\((?P<tag>[^)]*)\)\s*\)\s*return\s+AVERROR",
            re.DOTALL,
        )
        for m in pattern_mktag.finditer(media_src):
            offset_str = m.group("offset") or ""
            num_match = re.search(r"([+\-]?\d+)", offset_str)
            off = int(num_match.group(1)) if num_match else 0

            tag_str = m.group("tag")
            args = [a.strip() for a in tag_str.split(",") if a.strip()]
            tag_bytes = []
            for a in args:
                # Char literal
                m_char = re.match(r"'(.*)'", a)
                if m_char:
                    ch = m_char.group(1)
                    if not ch:
                        val = 0
                    else:
                        # Handle simple escape sequences
                        if ch[0] == "\\" and len(ch) >= 2:
                            esc = ch[1]
                            mapping = {
                                "0": 0,
                                "n": 10,
                                "r": 13,
                                "t": 9,
                                "\\": 92,
                                "'": 39,
                                '"': 34,
                            }
                            if esc in mapping:
                                val = mapping[esc]
                            else:
                                val = ord(ch[-1])
                        else:
                            val = ord(ch[0])
                    tag_bytes.append(val & 0xFF)
                else:
                    # Numeric literal
                    try:
                        val = int(a, 0)
                        tag_bytes.append(val & 0xFF)
                    except ValueError:
                        pass

            if not tag_bytes:
                continue

            for i, b in enumerate(tag_bytes):
                pos = pkt_offset + off + i
                if 0 <= pos < total_len:
                    buf[pos] = b & 0xFF

        # Direct byte comparisons: if (pkt->data[idx] != VAL) return AVERROR...
        pattern_byte = re.compile(
            r"if\s*\(\s*pkt->data\[(?P<idx>\d+)\]\s*!=\s*(?P<rhs>0x[0-9A-Fa-f]+|\d+|'[^']*')\s*\)\s*return\s+AVERROR",
            re.DOTALL,
        )
        for m in pattern_byte.finditer(media_src):
            try:
                idx = int(m.group("idx"))
            except ValueError:
                continue
            rhs = m.group("rhs")
            if rhs.startswith("'") and rhs.endswith("'"):
                ch = rhs[1:-1]
                val = ord(ch[0]) if ch else 0
            else:
                try:
                    val = int(rhs, 0)
                except ValueError:
                    continue
            pos = pkt_offset + idx
            if 0 <= pos < total_len:
                buf[pos] = val & 0xFF

        # Ensure pkt->size implied area is non-zero to avoid other corner checks
        # (if any), but generally the filter should accept arbitrary payload.
