#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    long long m;
    if (!(cin >> n >> m)) {
        return 0;
    }

    vector<vector<int>> g(n + 1);
    vector<int> eu(m), ev(m);

    for (long long i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        eu[i] = u;
        ev[i] = v;
        g[u].push_back(v);
        g[v].push_back(u);
    }

    vector<int> best_col(n + 1, 1);

    if (m == 0) {
        // No edges, any coloring is perfect
        cout << best_col[1];
        for (int i = 2; i <= n; ++i) {
            cout << ' ' << best_col[i];
        }
        cout << '\n';
        return 0;
    }

    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

    const int MAX_RESTARTS = 7;
    const int MAX_SWEEPS = 30;

    vector<int> col(n + 1);
    vector<int> order(n);
    iota(order.begin(), order.end(), 1);

    long long best_b = (long long)4e18;

    for (int r = 0; r < MAX_RESTARTS; ++r) {
        // Random initial coloring
        for (int v = 1; v <= n; ++v) {
            col[v] = (int)(rng() % 3) + 1;
        }

        // Compute initial number of conflicting edges
        long long b = 0;
        for (long long i = 0; i < m; ++i) {
            if (col[eu[i]] == col[ev[i]]) ++b;
        }

        for (int sweep = 0; sweep < MAX_SWEEPS; ++sweep) {
            bool improved = false;
            shuffle(order.begin(), order.end(), rng);

            for (int idx = 0; idx < n; ++idx) {
                int v = order[idx];
                int oldc = col[v];
                int cnt[4] = {0, 0, 0, 0};

                for (int u : g[v]) {
                    ++cnt[col[u]];
                }

                int bestc = oldc;
                int bestLocal = cnt[oldc];

                for (int c = 1; c <= 3; ++c) {
                    if (cnt[c] < bestLocal) {
                        bestLocal = cnt[c];
                        bestc = c;
                    }
                }

                if (bestc != oldc) {
                    b += (long long)cnt[bestc] - (long long)cnt[oldc];
                    col[v] = bestc;
                    improved = true;
                }
            }

            if (!improved) break;
        }

        if (b < best_b) {
            best_b = b;
            best_col = col;
            if (best_b == 0) break; // perfect coloring
        }
    }

    cout << best_col[1];
    for (int i = 2; i <= n; ++i) {
        cout << ' ' << best_col[i];
    }
    cout << '\n';

    return 0;
}