#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    int n;
    cin >> n;

    vector<int> left_cnt(n, -1), right_cnt(n, -1);
    vector<bool> visited(n, false);

    auto query = [&](int i) -> pair<int, int> {
        cout << "? " << i << endl;
        int a0, a1;
        cin >> a0 >> a1;
        return {a0, a1};
    };

    // query leftmost and rightmost
    auto [l0, r0] = query(0);
    visited[0] = true;
    left_cnt[0] = l0;
    right_cnt[0] = r0;
    if (l0 == 0 && r0 == 0) {
        cout << "! 0" << endl;
        return 0;
    }

    auto [ln, rn] = query(n - 1);
    visited[n - 1] = true;
    left_cnt[n - 1] = ln;
    right_cnt[n - 1] = rn;
    if (ln == 0 && rn == 0) {
        cout << "! " << n - 1 << endl;
        return 0;
    }

    int l = 0, r = n - 1;
    while (r - l > 1) {
        int m = (l + r) / 2;
        if (!visited[m]) {
            auto [lm, rm] = query(m);
            visited[m] = true;
            left_cnt[m] = lm;
            right_cnt[m] = rm;
            if (lm == 0 && rm == 0) {
                cout << "! " << m << endl;
                return 0;
            }
        }

        int d_m = left_cnt[m] + right_cnt[m];

        if (d_m == 1) {
            // type 2 box: diamond is on the side with count 1
            if (left_cnt[m] == 1) {
                r = m - 1;
            } else {
                l = m + 1;
            }
        } else {
            if (left_cnt[m] == 0) {
                // all more expensive boxes (including diamond) are to the right
                l = m + 1;
            } else if (right_cnt[m] == 0) {
                // all more expensive boxes are to the left
                r = m - 1;
            } else {
                // both sides have more expensive boxes – try to advance left bound
                if (l + 1 <= r) {
                    int nl = l + 1;
                    if (!visited[nl]) {
                        auto [lnl, rnl] = query(nl);
                        visited[nl] = true;
                        left_cnt[nl] = lnl;
                        right_cnt[nl] = rnl;
                        if (lnl == 0 && rnl == 0) {
                            cout << "! " << nl << endl;
                            return 0;
                        }
                        if (lnl == 0) {
                            l = nl;
                        } else if (rnl == 0) {
                            r = nl;
                        } else {
                            l = nl;
                        }
                    } else {
                        l = nl; // already queried, just move
                    }
                } else {
                    break; // interval is tiny, will linear scan
                }
            }
        }
    }

    // linear scan the remaining small interval
    for (int i = l; i <= r; ++i) {
        if (!visited[i]) {
            auto [li, ri] = query(i);
            if (li == 0 && ri == 0) {
                cout << "! " << i << endl;
                return 0;
            }
        } else {
            if (left_cnt[i] == 0 && right_cnt[i] == 0) {
                cout << "! " << i << endl;
                return 0;
            }
        }
    }

    // fallback (should not happen)
    cout << "! 0" << endl;
    return 0;
}