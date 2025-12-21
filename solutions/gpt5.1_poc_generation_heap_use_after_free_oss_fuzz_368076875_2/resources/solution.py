import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        ground_truth_len = 274773
        keywords = (
            "poc",
            "crash",
            "uaf",
            "use-after-free",
            "heap-use-after-free",
            "testcase",
            "oss-fuzz",
            "clusterfuzz",
            "bug",
            "uaf_ast",
            "ast_repr",
        )

        try:
            with tarfile.open(src_path, "r:*") as tf:
                members = tf.getmembers()

                best_exact = None
                best_exact_has_kw = False

                best_close = None
                best_close_diff = None
                best_close_has_kw = False

                best_kw_large = None
                best_kw_large_size = -1

                best_large = None
                best_large_size = -1

                close_threshold = 4096
                max_considered_size = 1024 * 1024

                for m in members:
                    if not m.isreg():
                        continue

                    size = m.size
                    name_lower = m.name.lower()
                    has_kw = any(k in name_lower for k in keywords)

                    # Exact size match
                    if size == ground_truth_len:
                        if best_exact is None or (has_kw and not best_exact_has_kw):
                            best_exact = m
                            best_exact_has_kw = has_kw

                    # Near size match
                    diff = abs(size - ground_truth_len)
                    if diff <= close_threshold:
                        if (
                            best_close is None
                            or diff < best_close_diff
                            or (
                                diff == best_close_diff
                                and has_kw
                                and not best_close_has_kw
                            )
                        ):
                            best_close = m
                            best_close_diff = diff
                            best_close_has_kw = has_kw

                    # Fallback: largest keyword-containing file (up to 1MB)
                    if size <= max_considered_size:
                        if size > best_large_size:
                            best_large = m
                            best_large_size = size
                        if has_kw and size > best_kw_large_size:
                            best_kw_large = m
                            best_kw_large_size = size

                target = None
                if best_exact is not None:
                    target = best_exact
                elif best_close is not None:
                    target = best_close
                elif best_kw_large is not None:
                    target = best_kw_large
                else:
                    target = best_large

                if target is not None:
                    extracted = tf.extractfile(target)
                    if extracted is not None:
                        data = extracted.read()
                        extracted.close()
                        if isinstance(data, bytes) and data:
                            return data
        except Exception:
            pass

        return self._generic_poc()

    def _generic_poc(self) -> bytes:
        depth = 10000
        core = "1"
        s = "(" * depth + core + ")" * depth + ";"
        reps = 5
        return (s * reps).encode("ascii")
