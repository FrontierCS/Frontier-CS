#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n, m;
    if (!(cin >> n >> m)) return 0;
    vector<vector<int>> g(n + 1);
    g.reserve(n + 1);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        g[u].push_back(v);
        g[v].push_back(u);
    }

    if (m == 0) {
        // Any coloring is fine
        for (int i = 1; i <= n; ++i) {
            int c = (i % 3) + 1;
            cout << c << (i == n ? '\n' : ' ');
        }
        return 0;
    }

    // Time management
    using clk = chrono::high_resolution_clock;
    auto t_start = clk::now();
    const double TIME_LIMIT = 1.7; // seconds

    // Data structures
    vector<int> color(n + 1), best_color(n + 1);
    struct C3 { int c[3]; };
    vector<C3> cnt(n + 1);

    // Random generator
    uint64_t seed = chrono::steady_clock::now().time_since_epoch().count();
    std::mt19937_64 rng(seed);
    auto rnd3 = [&]() -> int { return int(rng() % 3); };

    auto build_counts = [&](const vector<int>& col) {
        for (int i = 1; i <= n; ++i) {
            cnt[i].c[0] = cnt[i].c[1] = cnt[i].c[2] = 0;
        }
        for (int u = 1; u <= n; ++u) {
            int cu = col[u];
            for (int v : g[u]) {
                cnt[u].c[col[v]]++;
            }
        }
    };

    auto local_improve = [&]() {
        deque<int> dq;
        vector<char> inq(n + 1, 0);
        dq.clear();
        for (int i = 1; i <= n; ++i) {
            dq.push_back(i);
            inq[i] = 1;
        }
        while (!dq.empty()) {
            // Check time
            auto now = clk::now();
            double elapsed = chrono::duration<double>(now - t_start).count();
            if (elapsed > TIME_LIMIT) break;

            int v = dq.front(); dq.pop_front(); inq[v] = 0;
            int cur = color[v];
            int bestCol = cur;
            int bestVal = cnt[v].c[cur];
            for (int k = 0; k < 3; ++k) {
                int val = cnt[v].c[k];
                if (val < bestVal) {
                    bestVal = val;
                    bestCol = k;
                }
            }
            if (bestCol != cur) {
                // Move v from cur to bestCol
                for (int u : g[v]) {
                    cnt[u].c[cur]--;
                    cnt[u].c[bestCol]++;
                    if (!inq[u]) { dq.push_back(u); inq[u] = 1; }
                }
                color[v] = bestCol;
            }
        }
    };

    auto compute_conflicts = [&]() -> long long {
        long long b = 0;
        for (int u = 1; u <= n; ++u) {
            for (int v : g[u]) {
                if (u < v && color[u] == color[v]) b++;
            }
        }
        return b;
    };

    long long best_b = LLONG_MAX;

    int restarts = 0;
    while (true) {
        auto now = clk::now();
        double elapsed = chrono::duration<double>(now - t_start).count();
        if (elapsed > TIME_LIMIT) break;

        // Random initial coloring
        for (int i = 1; i <= n; ++i) color[i] = rnd3();

        build_counts(color);
        local_improve();

        long long b = compute_conflicts();
        if (b < best_b) {
            best_b = b;
            for (int i = 1; i <= n; ++i) best_color[i] = color[i];
        }
        restarts++;
    }

    // Output best coloring (convert 0..2 to 1..3)
    for (int i = 1; i <= n; ++i) {
        int c = (best_color[i] % 3) + 1;
        cout << c << (i == n ? '\n' : ' ');
    }

    return 0;
}