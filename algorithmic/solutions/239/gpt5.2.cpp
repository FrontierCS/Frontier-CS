#include <bits/stdc++.h>
using namespace std;

struct Op {
    int u, c, v;
};

static const int MAXV = 4097; // vertices are 0..n, n<=4096

static inline long long sumSmall(int n, int D) {
    // sum_{d=2..D} (n+1-d), with D clamped to <= n
    if (D < 2) return 0;
    long long nn = (long long)n + 1;
    long long DD = D;
    return (DD - 1) * nn - (DD * (DD + 1) / 2 - 1);
}

static inline long long sumArith(int n, long long step, int K) {
    // sum_{k=2..K} (n+1 - k*step)
    if (K < 2) return 0;
    long long nn = (long long)n + 1;
    long long KK = K;
    return (KK - 1) * nn - step * (KK * (KK + 1) / 2 - 1);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    if (n <= 3) {
        cout << 0 << '\n';
        return 0;
    }

    int V = n + 1;

    int bestA = 1, bestB = 1, bestC = 1;
    long long bestCost = LLONG_MAX;

    int maxParam = 128;

    for (int A = 1; A <= maxParam; ++A) {
        for (int B = 1; B <= maxParam; ++B) {
            long long AB = 1LL * A * B;
            for (int C = 1; C <= maxParam; ++C) {
                long long prod = AB * C;
                if (prod < (long long)n + 1) continue;

                long long cost = 0;

                int D = min(A, n);
                cost += sumSmall(n, D);

                if (A <= n) {
                    int K = min(B, n / A);
                    cost += sumArith(n, A, K);
                }

                if (AB <= n) {
                    int T = min(C, (int)(n / AB));
                    cost += sumArith(n, AB, T);
                }

                if (cost < bestCost || (cost == bestCost && (A + B + C) < (bestA + bestB + bestC))) {
                    bestCost = cost;
                    bestA = A;
                    bestB = B;
                    bestC = C;
                }
            }
        }
    }

    vector< bitset<MAXV> > adj(V);
    for (int i = 0; i < n; ++i) adj[i].set(i + 1);

    vector<Op> ops;
    ops.reserve((size_t)min<long long>(bestCost, 2000000LL));

    auto addEdge = [&](int u, int c, int v) {
        if (adj[u].test(v)) return;
        // Preconditions should hold by construction.
        // If they don't, we fall back to a safe (but potentially large) construction.
        if (!adj[u].test(c) || !adj[c].test(v)) {
            // Fallback: build u->v via chain using already existing consecutive edges.
            // This should never trigger for the intended construction.
            for (int x = u; x + 1 <= v; ++x) {
                // ensure edge u->x+1 exists by repeatedly shortcutting
                // Use intermediate x: need u->x and x->x+1
                if (x == u) continue; // u->u doesn't exist; u->u+1 already exists initially if v>=u+1 and u<n
                if (!adj[u].test(x)) continue;
                if (!adj[x].test(x + 1)) continue;
                if (!adj[u].test(x + 1)) {
                    adj[u].set(x + 1);
                    ops.push_back({u, x, x + 1});
                }
            }
            // Now try again with some c in (u,v)
            for (int mid = v - 1; mid > u; --mid) {
                if (adj[u].test(mid) && adj[mid].test(v)) {
                    adj[u].set(v);
                    ops.push_back({u, mid, v});
                    return;
                }
            }
            // As a last resort, do nothing (invalid), but this should not happen.
            return;
        }
        adj[u].set(v);
        ops.push_back({u, c, v});
    };

    int A = bestA, B = bestB, C = bestC;

    int D = min(A, n);
    for (int d = 2; d <= D; ++d) {
        for (int i = 0; i + d <= n; ++i) {
            int u = i;
            int v = i + d;
            int c = i + d - 1;
            addEdge(u, c, v);
        }
    }

    if (A <= n) {
        int K = min(B, n / A);
        for (int k = 2; k <= K; ++k) {
            int len = k * A;
            for (int i = 0; i + len <= n; ++i) {
                int u = i;
                int c = i + (k - 1) * A;
                int v = i + len;
                addEdge(u, c, v);
            }
        }
    }

    long long AB = 1LL * A * B;
    if (AB <= n) {
        int T = min(C, (int)(n / AB));
        for (int t = 2; t <= T; ++t) {
            long long len = 1LL * t * AB;
            for (int i = 0; i + len <= n; ++i) {
                int u = i;
                int c = i + (t - 1) * (int)AB;
                int v = i + (int)len;
                addEdge(u, c, v);
            }
        }
    }

    cout << ops.size() << '\n';
    for (const auto &op : ops) {
        cout << op.u << ' ' << op.c << ' ' << op.v << '\n';
    }

    return 0;
}