#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<vector<int>> g(n);
    vector<pair<int,int>> edges;
    edges.reserve(m);

    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        g[u].push_back(v);
        g[v].push_back(u);
        edges.emplace_back(u, v);
    }

    if (m == 0) {
        // Any coloring is perfect
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << 1;
        }
        cout << '\n';
        return 0;
    }

    // Greedy initialization by descending degree
    vector<int> col(n, 0);
    vector<int> orderDeg(n);
    iota(orderDeg.begin(), orderDeg.end(), 0);
    sort(orderDeg.begin(), orderDeg.end(), [&](int a, int b) {
        return g[a].size() > g[b].size();
    });

    for (int idx = 0; idx < n; ++idx) {
        int v = orderDeg[idx];
        int used[4] = {0,0,0,0};
        for (int nb : g[v]) {
            if (col[nb] != 0) used[col[nb]]++;
        }
        int bestC = 1;
        int bestVal = used[1];
        for (int c = 2; c <= 3; ++c) {
            if (used[c] < bestVal) {
                bestVal = used[c];
                bestC = c;
            }
        }
        col[v] = bestC;
    }

    // Neighbor color counts
    vector<array<int,4>> cnt(n);
    for (int i = 0; i < n; ++i) cnt[i] = {0,0,0,0};

    for (auto &e : edges) {
        int u = e.first, v = e.second;
        cnt[u][ col[v] ]++;
        cnt[v][ col[u] ]++;
    }

    long long bad = 0;
    for (int i = 0; i < n; ++i) {
        bad += cnt[i][ col[i] ];
    }
    bad /= 2;

    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());
    const double TIME_LIMIT = 0.95; // seconds
    auto start = chrono::steady_clock::now();

    vector<int> order(n);
    iota(order.begin(), order.end(), 0);

    const int MAX_SWEEPS = 200;
    for (int sweep = 0; sweep < MAX_SWEEPS; ++sweep) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - start).count();
        if (elapsed > TIME_LIMIT) break;

        bool improved = false;
        shuffle(order.begin(), order.end(), rng);

        for (int idx = 0; idx < n; ++idx) {
            int v = order[idx];
            int c0 = col[v];

            int bestC = c0;
            int bestDelta = 0;

            int c1 = (c0 % 3) + 1;
            int c2 = (c1 % 3) + 1;

            int delta1 = cnt[v][c1] - cnt[v][c0];
            if (delta1 < bestDelta) {
                bestDelta = delta1;
                bestC = c1;
            }
            int delta2 = cnt[v][c2] - cnt[v][c0];
            if (delta2 < bestDelta) {
                bestDelta = delta2;
                bestC = c2;
            }

            if (bestC != c0) {
                improved = true;
                bad += bestDelta;
                // Update neighbor counts
                for (int nb : g[v]) {
                    cnt[nb][c0]--;
                    cnt[nb][bestC]++;
                }
                col[v] = bestC;
            }
        }

        if (!improved) break;
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << col[i];
    }
    cout << '\n';

    return 0;
}