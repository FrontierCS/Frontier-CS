#include <bits/stdc++.h>
using namespace std;

const int MAXN = 5005;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;

    if (n <= 3) {
        cout << 0 << '\n';
        return 0;
    }

    auto count_edges = [&](int L1, int L2) -> long long {
        long long res = 0;
        int u = min(L1, n);
        if (u >= 2) {
            // S1: lengths 2..u
            res += (long long)(u - 1) * (n + 1) - ((long long)u * (u + 1) / 2 - 1);
        }
        int mmax = min(L2, n / L1);
        if (mmax >= 2) {
            // S2: m = 2..mmax, lengths m*L1
            res += (long long)(mmax - 1) * (n + 1) - (long long)L1 * ((long long)mmax * (mmax + 1) / 2 - 1);
        }
        long long step = 1LL * L1 * L2;
        if (step > 0) {
            int pmax = n / (int)step;
            if (pmax >= 2) {
                // S3: p = 2..pmax, lengths p*L1*L2
                res += (long long)(pmax - 1) * (n + 1) - step * ((long long)pmax * (pmax + 1) / 2 - 1);
            }
        }
        return res;
    };

    int bestL1 = 1, bestL2 = 1;
    long long best = LLONG_MAX;
    for (int L1 = 1; L1 <= n; ++L1) {
        // Precompute S1 part for this L1 to reduce repeated work
        long long baseS1 = 0;
        int u = min(L1, n);
        if (u >= 2) {
            baseS1 = (long long)(u - 1) * (n + 1) - ((long long)u * (u + 1) / 2 - 1);
        }
        for (int L2 = 1; L2 <= n; ++L2) {
            long long res = baseS1;
            int mmax = min(L2, n / L1);
            if (mmax >= 2) {
                res += (long long)(mmax - 1) * (n + 1) - (long long)L1 * ((long long)mmax * (mmax + 1) / 2 - 1);
            }
            long long step = 1LL * L1 * L2;
            if (step > 0) {
                int pmax = n / (int)step;
                if (pmax >= 2) {
                    res += (long long)(pmax - 1) * (n + 1) - step * ((long long)pmax * (pmax + 1) / 2 - 1);
                }
            }
            if (res < best) {
                best = res;
                bestL1 = L1;
                bestL2 = L2;
            }
        }
    }

    int N = n + 1;
    vector< bitset<MAXN> > adj(N);
    for (int i = 0; i < n; ++i) adj[i].set(i + 1);

    vector<array<int,3>> ops;
    auto add = [&](int u, int c, int v) {
        if (adj[u].test(v)) return;
        // Assumes adj[u][c] and adj[c][v] are already true by construction
        adj[u].set(v);
        ops.push_back({u, c, v});
    };

    int L1 = bestL1, L2 = bestL2;

    // S1: build lengths 2..L1
    for (int len = 2; len <= L1 && len <= n; ++len) {
        for (int a = 0; a + len <= n; ++a) {
            int c = a + len - 1;
            add(a, c, a + len);
        }
    }

    // S2: lengths m * L1 for m = 2..L2
    for (int m = 2; m <= L2; ++m) {
        int len = m * L1;
        if (len > n) break;
        for (int a = 0; a + len <= n; ++a) {
            int c = a + (m - 1) * L1;
            add(a, c, a + len);
        }
    }

    // S3: multiples of step = L1 * L2, p = 2..pmax
    long long step = 1LL * L1 * L2;
    if (step <= n) {
        int pmax = n / (int)step;
        for (int p = 2; p <= pmax; ++p) {
            int len = p * (int)step;
            for (int a = 0; a + len <= n; ++a) {
                int c = a + (p - 1) * (int)step;
                add(a, c, a + len);
            }
        }
    }

    cout << ops.size() << '\n';
    for (auto &e : ops) {
        cout << e[0] << ' ' << e[1] << ' ' << e[2] << '\n';
    }

    return 0;
}