#include <bits/stdc++.h>
using namespace std;

static const int MAXN = 500 + 5;
static const int MAXC = 500 + 5;

struct DSATURResult {
    vector<int> color;
    int usedColors;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, M;
    if(!(cin >> N >> M)) return 0;
    vector<bitset<MAXN>> adj(N+1);
    for (int i = 0; i < M; ++i) {
        int u, v; cin >> u >> v;
        if (u == v) continue;
        adj[u].set(v);
        adj[v].set(u);
    }
    // Build adjacency list (unique neighbors)
    vector<vector<int>> g(N+1);
    vector<int> degree(N+1, 0);
    for (int u = 1; u <= N; ++u) {
        for (int v = adj[u]._Find_first(); v <= N; v = adj[u]._Find_next(v)) {
            if (v == 0) continue; // bitset index 0 unused
            g[u].push_back(v);
        }
        degree[u] = (int)g[u].size();
    }

    auto run_dsat = [&](bool randomized, mt19937 &rng)->DSATURResult {
        vector<int> color(N+1, 0);
        vector< bitset<MAXC> > neighCols(N+1);
        vector<int> sat(N+1, 0);
        vector<char> uncolored(N+1, 1);
        int uncoloredCount = N;
        int maxColor = 0;

        while (uncoloredCount > 0) {
            int best = -1;
            int bestSat = -1;
            int bestDeg = -1;
            if (!randomized) {
                for (int v = 1; v <= N; ++v) if (uncolored[v]) {
                    if (sat[v] > bestSat || (sat[v] == bestSat && (degree[v] > bestDeg || (degree[v] == bestDeg && v < best)))) {
                        best = v;
                        bestSat = sat[v];
                        bestDeg = degree[v];
                    }
                }
            } else {
                // Collect candidates with max saturation
                for (int v = 1; v <= N; ++v) if (uncolored[v]) {
                    if (sat[v] > bestSat) {
                        bestSat = sat[v];
                    }
                }
                vector<int> cand;
                for (int v = 1; v <= N; ++v) if (uncolored[v] && sat[v] == bestSat) cand.push_back(v);
                // From cand, find max degree
                int maxDeg = -1;
                for (int v : cand) maxDeg = max(maxDeg, degree[v]);
                vector<int> cand2;
                for (int v : cand) if (degree[v] == maxDeg) cand2.push_back(v);
                uniform_int_distribution<int> dist(0, (int)cand2.size()-1);
                best = cand2[dist(rng)];
            }

            // choose smallest feasible color
            int chosen = 1;
            for (; chosen <= maxColor; ++chosen) {
                if (!neighCols[best].test(chosen)) break;
            }
            if (chosen == maxColor + 1) maxColor++;

            color[best] = chosen;
            uncolored[best] = 0;
            uncoloredCount--;

            // update neighbors
            for (int u : g[best]) if (uncolored[u]) {
                if (!neighCols[u].test(chosen)) {
                    neighCols[u].set(chosen);
                    sat[u]++;
                }
            }
        }

        return {color, maxColor};
    };

    auto try_reduce_colors = [&](vector<int> &color, int &maxColor) {
        // Attempt to reduce the number of colors by recoloring higher colors down
        vector<int> order;
        vector<int> colClassCount(maxColor+1, 0);
        for (int v = 1; v <= N; ++v) colClassCount[color[v]]++;
        bool improved = true;
        while (improved) {
            improved = false;
            for (int c = maxColor; c >= 2; --c) {
                // collect vertices of color c
                order.clear();
                for (int v = 1; v <= N; ++v) if (color[v] == c) order.push_back(v);
                if (order.empty()) continue;
                // try to recolor each vertex into a lower color
                bool allMoved = true;
                for (int v : order) {
                    bitset<MAXC> used;
                    for (int u : g[v]) {
                        int cu = color[u];
                        if (cu >= 1) used.set(cu);
                    }
                    int newc = 0;
                    for (int k = 1; k < c; ++k) {
                        if (!used.test(k)) { newc = k; break; }
                    }
                    if (newc == 0) {
                        allMoved = false;
                    } else {
                        color[v] = newc;
                    }
                }
                if (allMoved) {
                    // removed color c
                    maxColor--;
                    improved = true;
                    // No need to reindex colors; just continue trying more reductions
                } else {
                    // revert those who couldn't be recolored? We left recolored ones as is; it's okay as it may help later reductions.
                    // Ensure still valid: recoloring into non-conflicting colors maintains validity.
                }
            }
        }
    };

    // Time-bounded multi-start
    auto start = chrono::steady_clock::now();
    const double timeLimitSeconds = 1.9; // leave some margin
    mt19937 rng((uint32_t)chrono::high_resolution_clock::now().time_since_epoch().count());

    DSATURResult best = run_dsat(false, rng);
    try_reduce_colors(best.color, best.usedColors);

    int iterations = 1;
    while (true) {
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - start).count();
        if (elapsed > timeLimitSeconds) break;
        DSATURResult cur = run_dsat(true, rng);
        try_reduce_colors(cur.color, cur.usedColors);
        if (cur.usedColors < best.usedColors) {
            best = std::move(cur);
        }
        iterations++;
    }

    for (int i = 1; i <= N; ++i) {
        cout << best.color[i] << "\n";
    }
    return 0;
}