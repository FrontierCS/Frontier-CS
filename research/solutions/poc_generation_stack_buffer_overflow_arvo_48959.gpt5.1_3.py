import zlib


class Solution:
    def _generate_gzip_dynamic(self) -> bytes:
        wbits = 31  # gzip container with deflate
        best = None

        max_size = 2048
        size = 1
        prev_size = 0

        # Find a size where the first deflate block uses dynamic Huffman codes (BTYPE == 2)
        while size <= max_size:
            data = b"A" * size
            cobj = zlib.compressobj(level=9, wbits=wbits)
            comp = cobj.compress(data) + cobj.flush()
            if len(comp) > 10:  # 10-byte gzip header
                first = comp[10]
                btype = (first >> 1) & 3
                if btype == 2:
                    best = comp
                    break
            prev_size = size
            size *= 2

        if best is None:
            # Fallback: use some gzip-compressed data even if we didn't detect BTYPE=2
            data = b"A" * 32
            cobj = zlib.compressobj(level=9, wbits=wbits)
            return cobj.compress(data) + cobj.flush()

        # Refine search between prev_size+1 and size-1 for a shorter gzip still using dynamic Huffman
        for s in range(prev_size + 1, size):
            data = b"A" * s
            cobj = zlib.compressobj(level=9, wbits=wbits)
            comp = cobj.compress(data) + cobj.flush()
            if len(comp) <= 10:
                continue
            first = comp[10]
            btype = (first >> 1) & 3
            if btype == 2 and len(comp) < len(best):
                best = comp

        return best

    def solve(self, src_path: str) -> bytes:
        return self._generate_gzip_dynamic()
