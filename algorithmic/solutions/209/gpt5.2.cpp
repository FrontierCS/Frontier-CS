#include <bits/stdc++.h>
using namespace std;

static long long ask(int u, long long d) {
    cout << "? " << u << " " << d << "\n";
    cout.flush();
    long long ans;
    if (!(cin >> ans)) exit(0);
    if (ans == -1) exit(0);
    return ans;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int h;
    if (!(cin >> h)) return 0;
    long long n = (1LL << h) - 1;

    const long long d_find_root = h; // root has no nodes at distance h

    int posScan = 1;
    int cand = -1;

    // Find an initial root candidate (may have false positives if sums are zero).
    for (int u = posScan; u <= (int)n; u++) {
        long long x = ask(u, d_find_root);
        if (x == 0) {
            cand = u;
            posScan = u + 1;
            break;
        }
    }
    if (cand == -1) cand = 1;

    // Global sum of distance-1 answers: sum_v f_v * deg(v)
    long long D1 = 0;
    for (int u = 1; u <= (int)n; u++) {
        long long x = ask(u, 1);
        D1 += x;
    }

    while (true) {
        // Query candidate for all distances 1..h-1 (from root these are depth-layer sums).
        vector<long long> layer(h, 0);
        for (int d = 1; d <= h - 1; d++) layer[d] = ask(cand, d);

        long long L = layer[h - 1]; // leaves sum
        long long I = 0;            // internal non-root sum (depth 1..h-2)
        for (int d = 1; d <= h - 2; d++) I += layer[d];

        long long tmp = D1 - 3LL * I - L;
        if (tmp >= 0 && (tmp % 2LL == 0)) {
            long long rootW = tmp / 2LL;
            long long S = rootW + I + L;
            cout << "! " << S << "\n";
            cout.flush();
            return 0;
        }

        // If invalid, scan for another candidate with answer 0 at distance h.
        int nextCand = -1;
        for (int u = posScan; u <= (int)n; u++) {
            long long x = ask(u, d_find_root);
            if (x == 0) {
                nextCand = u;
                posScan = u + 1;
                break;
            }
        }
        if (nextCand == -1) {
            // Fallback: output 0 (should not happen on valid tests).
            cout << "! " << 0 << "\n";
            cout.flush();
            return 0;
        }
        cand = nextCand;
    }
}