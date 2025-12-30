#include <bits/stdc++.h>
using namespace std;

using int64 = long long;

static inline int64 norm(int64 x, int64 n) {
    x %= n;
    if (x < 0) x += n;
    return x;
}
static inline int64 mv(int64 u, int64 delta, int64 n) {
    // vertices are 1..n, treat u-1 as 0..n-1 coordinate
    int64 z = norm((u - 1) + delta, n);
    return z + 1;
}

int64 query(int64 x, int64 y) {
    cout << "? " << x << " " << y << endl;
    cout.flush();
    int64 ans;
    if (!(cin >> ans)) exit(0);
    return ans;
}

int readJudge() {
    int r;
    if (!(cin >> r)) exit(0);
    return r;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int64 n;
        cin >> n;

        auto find_threshold = [&](int dir) -> pair<bool,int64> {
            int64 L = 1, R = n / 2;
            int64 res = -1;
            while (L <= R) {
                int64 M = (L + R) >> 1;
                int64 y = mv(1, dir * M, n);
                int64 d = query(1, y);
                if (d < M) {
                    res = M;
                    R = M - 1;
                } else {
                    L = M + 1;
                }
            }
            if (res == -1) return {false, -1};
            return {true, res};
        };

        // Find a target r such that shortest path from 1 to r uses the chord
        auto th_cw = find_threshold(+1);
        auto th_ccw = find_threshold(-1);

        int chosen_dir = 0;
        int64 tChosen = -1;
        if (th_cw.first && th_ccw.first) {
            if (th_cw.second <= th_ccw.second) {
                chosen_dir = +1;
                tChosen = th_cw.second;
            } else {
                chosen_dir = -1;
                tChosen = th_ccw.second;
            }
        } else if (th_cw.first) {
            chosen_dir = +1;
            tChosen = th_cw.second;
        } else if (th_ccw.first) {
            chosen_dir = -1;
            tChosen = th_ccw.second;
        } else {
            // Fallback: choose opposite vertex (n even) or near-opposite (n odd)
            // This case should be rare/impossible theoretically, but handle anyway.
            chosen_dir = +1;
            tChosen = n / 2;
        }

        int64 r = mv(1, chosen_dir * tChosen, n);
        int64 D = query(1, r);
        if (D == 1) {
            // r is directly connected to 1 via chord
            cout << "! " << 1 << " " << r << endl;
            cout.flush();
            int res = readJudge();
            if (res == -1) return 0;
            continue;
        }

        // Determine direction to follow a shortest path from 1 to r
        int64 d2 = query(2, r);
        int64 dn = query(n, r);
        int dir = 0;
        if (d2 == D - 1) dir = +1;
        else if (dn == D - 1) dir = -1;
        else {
            // In rare cases both neighbors might be viable or none (shouldn't be none unless D==0)
            // Prefer +1 if ties or neither (fallback)
            if (d2 == D) dir = +1;
            else dir = -1;
        }

        // Binary search maximum k such that dist(mv(1, dir*k), r) == D - k
        int64 lo = 0, hi = D;
        while (lo < hi) {
            int64 mid = (lo + hi + 1) >> 1;
            int64 pos = mv(1, dir * mid, n);
            int64 distPR = query(pos, r);
            if (distPR == D - mid) {
                lo = mid;
            } else {
                hi = mid - 1;
            }
        }
        int64 K = lo;
        int64 u = mv(1, dir * K, n); // one endpoint

        // Remaining cycle distance from v to r after crossing chord
        int64 L2 = D - K - 1;
        // Candidates for the other endpoint v: the two vertices at cycle distance L2 from r
        int64 candA = mv(r, +L2, n);
        int64 candB = mv(r, -L2, n);

        auto isNeighborOnCycle = [&](int64 a, int64 b)->bool {
            return (mv(a, +1, n) == b) || (mv(a, -1, n) == b);
        };

        int64 v = -1;
        // Prefer candidate that is not a cycle neighbor and has distance 1
        if (!isNeighborOnCycle(u, candA)) {
            int64 dUA = query(u, candA);
            if (dUA == 1) v = candA;
        }
        if (v == -1) {
            if (!isNeighborOnCycle(u, candB)) {
                int64 dUB = query(u, candB);
                if (dUB == 1) v = candB;
            }
        }
        // If still not found due to degenerate case (e.g., L2==1 making cand be neighbor), try the other if distance 1 anyway
        if (v == -1) {
            int64 dUA = query(u, candA);
            if (dUA == 1) v = candA;
            else {
                int64 dUB = query(u, candB);
                if (dUB == 1) v = candB;
            }
        }
        if (v == -1) {
            // As a final fallback (shouldn't happen), scan a few positions around candidates
            // This is very unlikely; but we ensure to find v by probing symmetric possibilities.
            // We'll probe a small fixed set around both candidates within 3 steps to keep within query budget.
            bool found = false;
            for (int sgn : {+1, -1}) {
                for (int step = 2; step <= 5 && !found; ++step) {
                    int64 cand = mv(r, sgn * step, n);
                    if (!isNeighborOnCycle(u, cand)) {
                        int64 d = query(u, cand);
                        if (d == 1) {
                            v = cand;
                            found = true;
                        }
                    }
                }
                if (found) break;
            }
            if (!found) {
                // absolute fallback: probe random (deterministic) offsets
                for (int off = 0; off < 10 && !found; ++off) {
                    int64 cand = mv(u, (off + 2) * 1234567 % n, n);
                    if (!isNeighborOnCycle(u, cand)) {
                        int64 d = query(u, cand);
                        if (d == 1) {
                            v = cand; found = true;
                        }
                    }
                }
            }
            if (v == -1) {
                // If still not found, pick candA (should not happen; interactor likely consistent)
                v = candA;
            }
        }

        cout << "! " << u << " " << v << endl;
        cout.flush();
        int rj = readJudge();
        if (rj == -1) return 0;
    }
    return 0;
}