#include <bits/stdc++.h>
using namespace std;

struct Solver {
    int n, m;
    vector<vector<int>> adj;
    mt19937 rng;
    chrono::steady_clock::time_point start_time;
    int time_limit_ms = 1800;

    Solver(): rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count()) {}

    bool time_up() const {
        auto now = chrono::steady_clock::now();
        return chrono::duration_cast<chrono::milliseconds>(now - start_time).count() > time_limit_ms;
    }

    long long compute_b(const vector<int>& color, vector<array<int,3>>& degcnt) {
        for (int v = 0; v < n; ++v) {
            degcnt[v] = {0,0,0};
        }
        for (int v = 0; v < n; ++v) {
            int cv = color[v];
            for (int u : adj[v]) {
                int cu = color[u];
                degcnt[v][cu]++;
            }
        }
        long long B2 = 0;
        for (int v = 0; v < n; ++v) B2 += degcnt[v][color[v]];
        return B2 / 2;
    }

    void hill_climb(vector<int>& color, vector<array<int,3>>& degcnt, long long& b) {
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        while (!time_up()) {
            shuffle(order.begin(), order.end(), rng);
            bool improved = false;
            for (int idx = 0; idx < n; ++idx) {
                if ((idx & 63) == 0 && time_up()) return;
                int v = order[idx];
                int c = color[v];
                int bestC = c;
                int bestVal = degcnt[v][c];
                // try other colors
                for (int k = 0; k < 3; ++k) {
                    if (k == c) continue;
                    int val = degcnt[v][k];
                    if (val < bestVal) {
                        bestVal = val;
                        bestC = k;
                    }
                }
                if (bestC != c) {
                    int db = bestVal - degcnt[v][c]; // negative or zero; we ensure negative
                    if (db < 0) {
                        // apply move
                        for (int u : adj[v]) {
                            degcnt[u][c]--;
                            degcnt[u][bestC]++;
                        }
                        color[v] = bestC;
                        b += db;
                        improved = true;
                    }
                }
            }
            if (!improved) break;
        }
    }

    vector<int> greedy_degree_init() {
        vector<int> color(n, -1);
        vector<int> deg(n);
        for (int i = 0; i < n; ++i) deg[i] = (int)adj[i].size();
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        sort(order.begin(), order.end(), [&](int a, int b){ return deg[a] > deg[b]; });
        vector<array<int,3>> cnt(n);
        for (int i = 0; i < n; ++i) cnt[i] = {0,0,0};
        for (int v : order) {
            array<int,3> ccnt = {0,0,0};
            for (int u : adj[v]) if (color[u] != -1) ccnt[color[u]]++;
            int bestC = 0;
            int bestVal = ccnt[0];
            for (int k = 1; k < 3; ++k) {
                if (ccnt[k] < bestVal) {
                    bestVal = ccnt[k];
                    bestC = k;
                }
            }
            // small random tie-break
            vector<int> opts;
            for (int k = 0; k < 3; ++k) if (ccnt[k] == bestVal) opts.push_back(k);
            bestC = opts[rng() % opts.size()];
            color[v] = bestC;
        }
        return color;
    }

    vector<int> random_init() {
        vector<int> color(n);
        for (int i = 0; i < n; ++i) color[i] = rng() % 3;
        return color;
    }

    void run() {
        ios::sync_with_stdio(false);
        cin.tie(nullptr);

        int N, M;
        if (!(cin >> N >> M)) {
            return;
        }
        n = N; m = M;
        vector<pair<int,int>> edges;
        edges.reserve(m);
        vector<int> deg(n,0);
        for (int i = 0; i < m; ++i) {
            int u, v; cin >> u >> v;
            --u; --v;
            if (u == v) continue;
            edges.emplace_back(u, v);
            deg[u]++; deg[v]++;
        }
        adj.assign(n, {});
        for (int i = 0; i < n; ++i) adj[i].reserve(deg[i]);
        for (auto &e : edges) {
            int u = e.first, v = e.second;
            adj[u].push_back(v);
            adj[v].push_back(u);
        }

        start_time = chrono::steady_clock::now();

        vector<int> best_color(n, 0);
        long long best_b = LLONG_MAX;

        // Try greedy degree initialization
        {
            vector<int> color = greedy_degree_init();
            vector<array<int,3>> degcnt(n);
            long long b = compute_b(color, degcnt);
            hill_climb(color, degcnt, b);
            if (b < best_b) {
                best_b = b;
                best_color = color;
            }
        }

        // Random restarts within time
        while (!time_up()) {
            vector<int> color = random_init();
            vector<array<int,3>> degcnt(n);
            long long b = compute_b(color, degcnt);
            hill_climb(color, degcnt, b);
            if (b < best_b) {
                best_b = b;
                best_color = color;
            }
        }

        // Output colors as 1..3
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << (best_color[i] + 1);
        }
        cout << "\n";
    }
};

int main() {
    Solver().run();
    return 0;
}