#include <bits/stdc++.h>
using namespace std;

static inline int ceil_log_base(long double n, long double base) {
    long double qd = logl(n) / logl(base);
    long long q = (long long)ceill(qd - 1e-12L);
    if (q < 0) q = 0;
    while (powl(base, (long double)q) + 1e-12L < n) q++;
    while (q > 0 && powl(base, (long double)(q - 1)) >= n - 1e-12L) q--;
    return (int)q;
}

struct Interactor {
    int query(int l, int r) {
        cout << "? " << l << " " << r << "\n";
        cout.flush();
        int x;
        if (!(cin >> x)) exit(0);
        if (x == -1) exit(0);
        return x;
    }
    int mark(int a) {
        cout << "! " << a << "\n";
        cout.flush();
        int y;
        if (!(cin >> y)) exit(0);
        if (y == -1) exit(0);
        return y;
    }
    void end_case() {
        cout << "#\n";
        cout.flush();
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    Interactor io;

    int t;
    if (!(cin >> t)) return 0;

    // States:
    // 0: start (no bits yet)
    // 1: last 0
    // 2: last 1
    // 3: 00
    // 4: 01
    // 5: 10
    // 6: 11
    int nxt[7][2];
    for (int s = 0; s < 7; s++) for (int b = 0; b < 2; b++) nxt[s][b] = -1;
    nxt[0][0] = 1; nxt[0][1] = 2;
    nxt[1][0] = 3; nxt[1][1] = 4;
    nxt[2][0] = 5; nxt[2][1] = 6;
    nxt[3][0] = -1; nxt[3][1] = 4;
    nxt[4][0] = 5; nxt[4][1] = 6;
    nxt[5][0] = 3; nxt[5][1] = 4;
    nxt[6][0] = 5; nxt[6][1] = -1;

    auto valid = [&](int s, int b) -> int { return nxt[s][b] != -1; };

    const long double BASE = 1.116L;

    while (t--) {
        int n;
        cin >> n;

        int q = ceil_log_base((long double)n, BASE);
        int Qmax = 2 * q;

        vector<int8_t> st(n + 1, 0); // all in start
        int alive = n;
        int used = 0;

        while (alive > 2 && used < Qmax) {
            // totals
            int cnt00 = 0, cnt11 = 0;
            int total15 = 0, total24 = 0; // counts of states {1,5} and {2,4}
            for (int i = 1; i <= n; i++) {
                int s = st[i];
                if (s < 0) continue;
                if (s == 3) cnt00++;
                else if (s == 6) cnt11++;
                if (s == 1 || s == 5) total15++;
                else if (s == 2 || s == 4) total24++;
            }

            int totalValid0 = alive - cnt00; // l=0 invalid only for 00
            int totalValid1 = alive - cnt11; // l=1 invalid only for 11

            long long bestWorst = (1LL << 60);
            long long bestImb = (1LL << 60);
            long long bestPrep = -1;
            int bestM = 1;

            int delta = 0;       // sum prefix (valid1-valid0), only +1 for 00 and -1 for 11
            int prefAlive = 0;
            int pref15 = 0, pref24 = 0;

            for (int m = 1; m <= n; m++) {
                int s = st[m];
                if (s >= 0) {
                    prefAlive++;
                    if (s == 3) delta++;
                    else if (s == 6) delta--;
                    if (s == 1 || s == 5) pref15++;
                    else if (s == 2 || s == 4) pref24++;
                }

                long long surv0 = (long long)totalValid0 + delta; // answer A=0: left l=1, right l=0
                long long surv1 = (long long)totalValid1 - delta; // answer A=1: left l=0, right l=1

                long long worst = 0;
                if (surv0 > 0) worst = max(worst, surv0);
                if (surv1 > 0) worst = max(worst, surv1);
                if (worst == 0) continue; // should be impossible

                long long imb = llabs(2LL * prefAlive - (long long)alive);

                int right15 = total15 - pref15;
                int left15 = pref15;
                int right24 = total24 - pref24;
                int left24 = pref24;

                long long min0 = min((long long)right15, (long long)left24); // if A=0, new00 from right15, new11 from left24
                long long min1 = min((long long)left15, (long long)right24); // if A=1, new00 from left15, new11 from right24
                long long prep = min(min0, min1);

                if (worst < bestWorst ||
                    (worst == bestWorst && imb < bestImb) ||
                    (worst == bestWorst && imb == bestImb && prep > bestPrep)) {
                    bestWorst = worst;
                    bestImb = imb;
                    bestPrep = prep;
                    bestM = m;
                }
            }

            int m = bestM;
            int x = io.query(1, m);
            int A = (x == m - 1) ? 1 : 0;

            int lLeft = A ^ 1; // P=1
            int lRight = A;    // P=0

            // update states
            for (int i = 1; i <= m; i++) {
                int s = st[i];
                if (s < 0) continue;
                int ns = nxt[s][lLeft];
                if (ns == -1) {
                    st[i] = -1;
                    alive--;
                } else st[i] = (int8_t)ns;
            }
            for (int i = m + 1; i <= n; i++) {
                int s = st[i];
                if (s < 0) continue;
                int ns = nxt[s][lRight];
                if (ns == -1) {
                    st[i] = -1;
                    alive--;
                } else st[i] = (int8_t)ns;
            }

            used++;
        }

        vector<int> cand;
        cand.reserve(4);
        for (int i = 1; i <= n; i++) if (st[i] >= 0) cand.push_back(i);

        // Mark up to 2 candidates
        if (!cand.empty()) {
            int y = io.mark(cand[0]);
            if (y != 1) {
                if ((int)cand.size() >= 2) {
                    io.mark(cand[1]);
                } else {
                    // Should not happen if consistent; do nothing further.
                }
            }
        } else {
            // Should never happen; fallback to marking 1 and 2
            io.mark(1);
            io.mark(2);
        }

        io.end_case();
    }
    return 0;
}