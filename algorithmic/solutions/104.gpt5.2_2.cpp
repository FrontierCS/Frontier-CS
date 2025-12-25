#include <bits/stdc++.h>
using namespace std;

static inline void die() {
    exit(0);
}

struct Solver {
    int n;
    int maxQ;

    vector<uint8_t> alive;
    vector<int8_t> prev1; // last D
    vector<int8_t> prev2; // second last D

    int ask(int l, int r) {
        cout << "? " << l << " " << r << "\n";
        cout.flush();
        int x;
        if (!(cin >> x)) die();
        if (x < 0) die();
        return x;
    }

    int mark(int a) {
        cout << "! " << a << "\n";
        cout.flush();
        int y;
        if (!(cin >> y)) die();
        if (y < 0) die();
        return y;
    }

    void finish_case() {
        cout << "#\n";
        cout.flush();
    }

    void solve_one(int N) {
        n = N;
        long double base = 1.116L;
        long double qv = log((long double)n) / log(base);
        int q = (int)ceill(qv - 1e-18L);
        if (q < 1) q = 1;
        maxQ = 2 * q;

        alive.assign(n + 1, 1);
        prev1.assign(n + 1, -1);
        prev2.assign(n + 1, -1);

        int aliveCnt = n;
        int queriesUsed = 0;

        vector<uint8_t> can0(n + 1), can1(n + 1);

        while (aliveCnt > 2 && queriesUsed < maxQ) {
            long long totalC0 = 0, totalC1 = 0;
            // Compute can0/can1 and totals
            for (int i = 1; i <= n; i++) {
                if (!alive[i]) {
                    can0[i] = can1[i] = 0;
                    continue;
                }
                bool c0 = true, c1 = true;
                if (prev2[i] != -1 && prev1[i] != -1 && prev2[i] == prev1[i]) {
                    if (prev1[i] == 0) c0 = false;
                    else c1 = false;
                }
                can0[i] = (uint8_t)c0;
                can1[i] = (uint8_t)c1;
                totalC0 += c0;
                totalC1 += c1;
            }

            long long L0 = 0, L1 = 0;
            int LA = 0;
            long long bestWorst = (1LL << 62);
            int bestImb = INT_MAX;
            int bestMid = 1;

            // Choose mid in [1, n-1]
            for (int mid = 1; mid <= n - 1; mid++) {
                if (alive[mid]) LA++;
                L0 += can0[mid];
                L1 += can1[mid];

                int RA = aliveCnt - LA;
                long long R0 = totalC0 - L0;
                long long R1 = totalC1 - L1;

                long long survive_b0 = L1 + R0; // b=0 => left D=1, right D=0
                long long survive_b1 = L0 + R1; // b=1 => left D=0, right D=1
                long long worst = max(survive_b0, survive_b1);

                int imb = abs(LA - RA);
                if (worst < bestWorst || (worst == bestWorst && imb < bestImb)) {
                    bestWorst = worst;
                    bestImb = imb;
                    bestMid = mid;
                }
            }

            int mid = bestMid;
            int x = ask(1, mid);
            queriesUsed++;

            int b = (x == mid) ? 0 : 1; // b=1 iff x==mid-1

            // Update candidates
            for (int i = 1; i <= n; i++) {
                if (!alive[i]) continue;
                int T = (i <= mid) ? 1 : 0;
                int newD = b ^ T;

                if (prev2[i] != -1 && prev1[i] != -1 && prev2[i] == prev1[i] && prev1[i] == newD) {
                    alive[i] = 0;
                    aliveCnt--;
                } else {
                    prev2[i] = prev1[i];
                    prev1[i] = (int8_t)newD;
                }
            }
        }

        vector<int> cand;
        cand.reserve(4);
        for (int i = 1; i <= n; i++) if (alive[i]) cand.push_back(i);

        if (cand.empty()) {
            // Shouldn't happen; fallback
            int y = mark(1);
            if (y == 0) mark(2);
            finish_case();
            return;
        }

        // Mark at most two
        int y1 = mark(cand[0]);
        if (y1 == 1) {
            finish_case();
            return;
        }
        int second = -1;
        if ((int)cand.size() >= 2) second = cand[1];
        else second = (cand[0] == 1 ? 2 : 1);

        mark(second);
        finish_case();
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int t;
    if (!(cin >> t)) return 0;
    Solver solver;
    while (t--) {
        int n;
        cin >> n;
        solver.solve_one(n);
    }
    return 0;
}