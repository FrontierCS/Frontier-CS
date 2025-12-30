#include <iostream>
#include <cstdlib>

using namespace std;

void answer(int i) {
    cout << "! " << i << endl;
    cout.flush();
    exit(0);
}

void query(int i, int& L, int& R) {
    cout << "? " << i << endl;
    cout.flush();
    cin >> L >> R;
    if (L == 0 && R == 0) {
        answer(i);
    }
}

int main() {
    int n;
    cin >> n;

    int L0, R0;
    query(0, L0, R0);          // left endpoint

    if (n == 1) {
        answer(0);
    }

    int Ln, Rn;
    query(n - 1, Ln, Rn);      // right endpoint

    int l = 0, r = n - 1;      // invariant: box l has L_l=0, box r has R_r=0

    while (r - l > 1) {
        if (r - l <= 100) {    // small interval -> linear scan
            for (int i = l + 1; i < r; ++i) {
                int L, R;
                query(i, L, R);
            }
            break;
        }

        int m = (l + r) / 2;
        int Lm, Rm;
        query(m, Lm, Rm);

        if (Lm == 0) {
            l = m;
        } else if (Rm == 0) {
            r = m;
        } else {               // both Lm>0 and Rm>0
            int p = (l + m) / 2;
            if (p != l && p != m) {
                int Lp, Rp;
                query(p, Lp, Rp);
                if (Lp == 0) {
                    l = p;
                    continue;
                } else if (Rp == 0) {
                    r = p;
                    continue;
                }
                // p also has both >0, try the right side
            }

            int q = (m + r) / 2;
            if (q != m && q != r) {
                int Lq, Rq;
                query(q, Lq, Rq);
                if (Lq == 0) {
                    l = q;
                    continue;
                } else if (Rq == 0) {
                    r = q;
                    continue;
                }
                // q also has both >0
            }

            // fallback: linear scan the whole interval
            for (int i = l + 1; i < r; ++i) {
                int L, R;
                query(i, L, R);
            }
            break;
        }
    }

    // safety answer (should never be reached if diamond is in (l,r))
    answer(l + 1);
    return 0;
}