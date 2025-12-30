#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;
    int N = n * m;

    int qcnt = 0;
    const int Q_LIMIT = 30000;

    auto query = [&](int ring, int dir) -> int {
        cout << "? " << ring << " " << dir << '\n';
        cout.flush();
        int a;
        if (!(cin >> a)) exit(0);
        ++qcnt;
        return N - a; // return number of blocked sections
    };

    // Initial query to get starting TOT (blocked count)
    int TOT = query(0, 1); // rotate ring 0 once clockwise

    // Coordinate descent: repeatedly try to reduce TOT
    // using single-step CW/CCW rotations per ring.
    while (TOT > m && qcnt + 5 * n <= Q_LIMIT) {
        int TOT_before = TOT;

        // Process rings in fixed order; no randomness needed
        for (int i = 0; i < n && qcnt + 5 <= Q_LIMIT; ++i) {
            int TOT0 = TOT; // current blocked count at base orientation

            // Try clockwise
            int TOT_cw = query(i, 1);   // orientation: base + 1
            int TOT_back = query(i, -1); // back to base
            TOT = TOT_back;
            TOT0 = TOT_back; // ensure consistency

            // Try counter-clockwise
            int TOT_ccw = query(i, -1); // orientation: base - 1
            TOT = TOT_ccw;

            // Decide best among base (TOT0), cw (TOT_cw), ccw (TOT_ccw)
            int best_state = -1; // -1 = ccw, 0 = base, 1 = cw
            int best_val = TOT_ccw;

            if (TOT0 < best_val) {
                best_val = TOT0;
                best_state = 0;
            }
            if (TOT_cw < best_val) {
                best_val = TOT_cw;
                best_state = 1;
            }

            if (best_state == -1) {
                // ccw is best; already there
                TOT = TOT_ccw;
            } else if (best_state == 0) {
                // base is best; from ccw move one step cw
                if (qcnt >= Q_LIMIT) break;
                TOT = query(i, 1); // ccw -> base
            } else {
                // cw is best; from ccw move two steps cw
                if (qcnt + 2 > Q_LIMIT) {
                    if (qcnt < Q_LIMIT) {
                        // at least go back to base
                        TOT = query(i, 1); // ccw -> base
                    }
                    break;
                } else {
                    TOT = query(i, 1); // ccw -> base
                    TOT = query(i, 1); // base -> cw
                }
            }
        }

        if (TOT == m) break;
        if (TOT == TOT_before) {
            // No improvement in this pass; further passes unlikely to help
            break;
        }
    }

    // At TOT == m, all arcs coincide (each arc length m and union size m).
    // Then all relative offsets p_i are 0.
    cout << "!";
    for (int i = 1; i < n; ++i) cout << " " << 0;
    cout << '\n';
    cout.flush();

    return 0;
}