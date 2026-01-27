#include <bits/stdc++.h>
using namespace std;

struct MaxCutSolver {
    int n, m;
    vector<vector<int>> adj;
    vector<pair<int,int>> edges;
    mt19937 rng;

    MaxCutSolver(int n, int m): n(n), m(m), adj(n), rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count()) {}

    void add_edge(int u, int v) {
        --u; --v;
        adj[u].push_back(v);
        adj[v].push_back(u);
        edges.emplace_back(u, v);
    }

    long long cut_value(const vector<int>& side) {
        long long c = 0;
        for (auto &e : edges) if (side[e.first] != side[e.second]) ++c;
        return c;
    }

    // Perform hill-climbing by flipping single vertices with positive gain
    long long local_search(vector<int>& side) {
        int n = side.size();
        vector<int> deg_cross(n, 0);
        for (auto &e : edges) {
            int u = e.first, v = e.second;
            if (side[u] != side[v]) {
                deg_cross[u]++; deg_cross[v]++;
            }
        }
        vector<int> deg(n);
        for (int i = 0; i < n; ++i) deg[i] = (int)adj[i].size();

        vector<int> gain(n);
        for (int i = 0; i < n; ++i) gain[i] = (deg[i] - 2 * deg_cross[i]); // deg_same - deg_cross

        // Greedy flips picking the vertex with maximum positive gain each time
        while (true) {
            int best_v = -1;
            int best_g = 0;
            for (int v = 0; v < n; ++v) {
                if (gain[v] > best_g) {
                    best_g = gain[v];
                    best_v = v;
                }
            }
            if (best_g <= 0) break;

            int v = best_v;
            int old_side = side[v];
            side[v] ^= 1;

            // Update neighbors
            for (int u : adj[v]) {
                // Before flip: edge (u,v) was cross if side[u] != old_side
                bool was_cross = (side[u] != old_side);
                if (was_cross) {
                    // becomes same -> deg_cross[u]--, deg_cross[v]--
                    deg_cross[u]--;
                    deg_cross[v]--;
                } else {
                    // becomes cross -> deg_cross[u]++, deg_cross[v]++
                    deg_cross[u]++;
                    deg_cross[v]++;
                }
                // Update gain[u] = deg[u] - 2*deg_cross[u]
                gain[u] = deg[u] - 2 * deg_cross[u];
            }
            // Update gain[v]
            gain[v] = deg[v] - 2 * deg_cross[v];
        }
        return cut_value(side);
    }

    vector<int> greedy_init_ordered() {
        vector<int> side(n, 0);
        vector<int> assigned(n, 0);
        vector<int> count_to0(n, 0), count_to1(n, 0);
        vector<int> order(n);
        iota(order.begin(), order.end(), 0);
        // Shuffle order to avoid bias
        shuffle(order.begin(), order.end(), rng);
        for (int idx = 0; idx < n; ++idx) {
            int v = order[idx];
            int s0 = count_to1[v]; // edges crossing if put in 0 equals neighbors already in 1
            int s1 = count_to0[v]; // edges crossing if put in 1 equals neighbors already in 0
            side[v] = (s1 > s0) ? 1 : 0;
            assigned[v] = 1;
            for (int u : adj[v]) {
                if (!assigned[u]) {
                    if (side[v] == 0) count_to0[u]++;
                    else count_to1[u]++;
                }
            }
        }
        return side;
    }

    vector<int> random_init() {
        vector<int> side(n);
        for (int i = 0; i < n; ++i) side[i] = uniform_int_distribution<int>(0,1)(rng);
        return side;
    }

    vector<int> solve() {
        if (m == 0) {
            return vector<int>(n, 0);
        }
        long long best_cut = -1;
        vector<int> best_side(n, 0);

        // Try one greedy initialization
        {
            vector<int> side = greedy_init_ordered();
            local_search(side);
            long long cv = cut_value(side);
            if (cv > best_cut) {
                best_cut = cv;
                best_side = side;
            }
        }

        // Multiple random restarts
        int restarts = 30;
        for (int r = 0; r < restarts; ++r) {
            vector<int> side = random_init();
            local_search(side);
            long long cv = cut_value(side);
            if (cv > best_cut) {
                best_cut = cv;
                best_side = side;
            }
        }

        return best_side;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) return 0;
    MaxCutSolver solver(n, m);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
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