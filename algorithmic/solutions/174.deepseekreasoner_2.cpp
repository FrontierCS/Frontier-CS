#include <bits/stdc++.h>
using namespace std;

struct Graph {
    int n;
    vector<vector<int>> adj;
    Graph(int n) : n(n), adj(n + 1) {}
    void add_edge(int u, int v) {
        adj[u].push_back(v);
        adj[v].push_back(u);
    }
};

// Performs up to max_passes of local improvement on a given coloring.
// Returns the improved coloring and the number of conflicting edges.
pair<vector<int>, int> local_improve(const Graph& g, vector<int> color, int max_passes, mt19937& rng) {
    int n = g.n;
    vector<array<int, 4>> cnt(n + 1); // indices 1..3
    for (int v = 1; v <= n; ++v)
        cnt[v].fill(0);

    // Build neighbor color counts
    for (int v = 1; v <= n; ++v)
        for (int u : g.adj[v])
            cnt[v][color[u]]++;

    // Compute initial conflicts
    int total_conflicts = 0;
    for (int v = 1; v <= n; ++v)
        total_conflicts += cnt[v][color[v]];
    total_conflicts /= 2;

    bool improvement = true;
    int passes = 0;
    vector<int> order(n);
    iota(order.begin(), order.end(), 1);

    while (improvement && passes < max_passes) {
        improvement = false;
        shuffle(order.begin(), order.end(), rng);
        for (int v : order) {
            int old_color = color[v];
            int best_color = old_color;
            int best_delta = 0; // negative is improvement
            for (int new_color = 1; new_color <= 3; ++new_color) {
                if (new_color == old_color) continue;
                int delta = cnt[v][new_color] - cnt[v][old_color];
                if (delta < best_delta) {
                    best_delta = delta;
                    best_color = new_color;
                }
            }
            if (best_color != old_color) {
                // Recolor vertex v
                color[v] = best_color;
                total_conflicts += best_delta;
                // Update neighbor counts
                for (int u : g.adj[v]) {
                    cnt[u][old_color]--;
                    cnt[u][best_color]++;
                }
                improvement = true;
            }
        }
        passes++;
    }
    return {color, total_conflicts};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    cin >> n >> m;
    Graph g(n);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        g.add_edge(u, v);
    }

    // Trivial case: no edges
    if (m == 0) {
        for (int i = 1; i <= n; ++i)
            cout << 1 << " \n"[i == n];
        return 0;
    }

    // Random number generator
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

    vector<int> best_coloring(n + 1);
    int best_conflicts = m + 1; // worst possible is m

    const int ITERATIONS = 50;
    const int IMPROVE_PASSES = 5;

    for (int iter = 0; iter < ITERATIONS; ++iter) {
        // Random vertex order for greedy coloring
        vector<int> order(n);
        iota(order.begin(), order.end(), 1);
        shuffle(order.begin(), order.end(), rng);

        // Greedy coloring
        vector<int> color(n + 1, 0);
        for (int v : order) {
            array<int, 4> cnt_nei = {0, 0, 0, 0};
            for (int u : g.adj[v])
                if (color[u] != 0)
                    cnt_nei[color[u]]++;

            int best_c = 1;
            int min_cnt = cnt_nei[1];
            for (int c = 2; c <= 3; ++c) {
                if (cnt_nei[c] < min_cnt) {
                    min_cnt = cnt_nei[c];
                    best_c = c;
                } else if (cnt_nei[c] == min_cnt && uniform_int_distribution<>(0, 1)(rng)) {
                    best_c = c; // random tie‑break
                }
            }
            color[v] = best_c;
        }

        // Local improvement
        auto [improved_color, conflicts] = local_improve(g, color, IMPROVE_PASSES, rng);

        if (conflicts < best_conflicts) {
            best_conflicts = conflicts;
            best_coloring = improved_color;
        }
    }

    for (int i = 1; i <= n; ++i)
        cout << best_coloring[i] << " \n"[i == n];
    return 0;
}