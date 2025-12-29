#include <bits/stdc++.h>
using namespace std;

struct Solver {
    int n, m;
    vector<vector<int>> g;
    vector<int> deg;
    mt19937 rng;

    Solver(int n, int m) : n(n), m(m), g(n), deg(n, 0) {
        rng.seed(chrono::steady_clock::now().time_since_epoch().count());
    }

    void add_edge(int u, int v) {
        g[u].push_back(v);
        g[v].push_back(u);
        deg[u]++;
        deg[v]++;
    }

    pair<long long, vector<int>> run_trial(const vector<int>& order) {
        vector<int> color(n, -1);
        // Initial greedy assignment based on given order
        for (int v : order) {
            int cntc[3] = {0, 0, 0};
            for (int u : g[v]) {
                if (color[u] != -1) cntc[color[u]]++;
            }
            int minv = min({cntc[0], cntc[1], cntc[2]});
            int choices[3], sz = 0;
            for (int c = 0; c < 3; ++c) if (cntc[c] == minv) choices[sz++] = c;
            uniform_int_distribution<int> dist(0, sz - 1);
            color[v] = choices[dist(rng)];
        }

        vector<array<int,3>> cnt(n);
        for (int i = 0; i < n; ++i) cnt[i] = {0,0,0};
        for (int v = 0; v < n; ++v) {
            auto &a = cnt[v];
            for (int u : g[v]) {
                a[color[u]]++;
            }
        }

        long long conf = 0;
        for (int v = 0; v < n; ++v) conf += cnt[v][color[v]];
        conf /= 2;

        // Local improvement using queue
        queue<int> q;
        vector<char> inq(n, 1);
        for (int v = 0; v < n; ++v) q.push(v);

        while (!q.empty()) {
            int v = q.front(); q.pop(); inq[v] = 0;
            int cur = color[v];
            int bestColor = cur;
            int bestCount = cnt[v][cur];
            for (int c = 0; c < 3; ++c) {
                if (cnt[v][c] < bestCount) {
                    bestCount = cnt[v][c];
                    bestColor = c;
                }
            }
            if (bestColor != cur) {
                int oldSame = cnt[v][cur];
                int newSame = cnt[v][bestColor];
                conf += (long long)newSame - oldSame; // delta (negative if improved)
                color[v] = bestColor;
                for (int u : g[v]) {
                    cnt[u][cur]--;
                    cnt[u][bestColor]++;
                    if (!inq[u]) { q.push(u); inq[u] = 1; }
                }
                if (!inq[v]) { q.push(v); inq[v] = 1; }
            }
        }

        return {conf, color};
    }

    vector<int> solve() {
        vector<int> bestColor(n, 0);
        long long bestConf = (long long)m; // worst case, all edges conflict

        int trials = 3;
        if (m > 400000) trials = 1;
        else if (m > 200000) trials = 2;

        vector<vector<int>> orders;

        // Trial 1: degree descending
        {
            vector<int> order(n);
            iota(order.begin(), order.end(), 0);
            sort(order.begin(), order.end(), [&](int a, int b){
                if (deg[a] != deg[b]) return deg[a] > deg[b];
                return a < b;
            });
            orders.push_back(move(order));
        }

        if (trials >= 2) {
            // Trial 2: random
            vector<int> order(n);
            iota(order.begin(), order.end(), 0);
            shuffle(order.begin(), order.end(), rng);
            orders.push_back(move(order));
        }

        if (trials >= 3) {
            // Trial 3: degree ascending
            vector<int> order(n);
            iota(order.begin(), order.end(), 0);
            sort(order.begin(), order.end(), [&](int a, int b){
                if (deg[a] != deg[b]) return deg[a] < deg[b];
                return a < b;
            });
            orders.push_back(move(order));
        }

        for (auto &order : orders) {
            auto res = run_trial(order);
            if (res.first < bestConf) {
                bestConf = res.first;
                bestColor = move(res.second);
                if (bestConf == 0) break;
            }
        }

        // Convert to 1-based colors
        for (int i = 0; i < n; ++i) bestColor[i] += 1;
        return bestColor;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    Solver solver(n, m);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        solver.add_edge(u, v);
    }
    vector<int> ans = solver.solve();
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << ans[i];
    }
    cout << '\n';
    return 0;
}