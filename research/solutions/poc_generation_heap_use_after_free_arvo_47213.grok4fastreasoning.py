class Solution:
    def solve(self, src_path: str) -> bytes:
        num = 3633
        elements = '1' + ',1' * (num - 1)
        code = 'a=' + '[' + elements + ']\n'
        return code.encode()