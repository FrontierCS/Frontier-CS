#include <bits/stdc++.h>
using namespace std;

struct Timer {
    chrono::steady_clock::time_point start;
    Timer() { start = chrono::steady_clock::now(); }
    double elapsed_ms() const {
        auto now = chrono::steady_clock::now();
        return chrono::duration<double, milli>(now - start).count();
    }
    chrono::steady_clock::time_point deadline(double ms) const {
        return start + chrono::milliseconds((long long)ms);
    }
};

struct LocalSearch {
    int n;
    const vector<vector<int>>& g;
    vector<int> col;
    vector<array<int,3>> cnt; // cnt[v][c] = number of neighbors of v with color c
    vector<int> bestColor;
    vector<int> curDelta;
    long long conflicts;
    mt19937 &rng;

    LocalSearch(const vector<vector<int>>& graph, vector<int> initialCol, mt19937& rngRef)
        : n((int)graph.size()), g(graph), col(move(initialCol)), cnt(n), bestColor(n), curDelta(n), conflicts(0), rng(rngRef) {}

    void buildCounts() {
        for (int v = 0; v < n; ++v) cnt[v] = {0,0,0};
        for (int v = 0; v < n; ++v) {
            int c = col[v];
            for (int u : g[v]) {
                cnt[u][c]++;
            }
        }
        long long b = 0;
        for (int v = 0; v < n; ++v) b += cnt[v][col[v]];
        conflicts = b / 2;
    }

    inline void recomputeVertex(int v) {
        int ccur = col[v];
        int minCount = cnt[v][0];
        int cMin = 0;
        // Random tie-breaking: shuffle colors order a bit
        int order[3] = {0,1,2};
        // Slight randomization
        if ((rng() & 1u) == 1u) swap(order[0], order[1]);
        if ((rng() & 2u) == 2u) swap(order[1], order[2]);
        minCount = INT_MAX;
        for (int i = 0; i < 3; ++i) {
            int c = order[i];
            if (cnt[v][c] < minCount) {
                minCount = cnt[v][c];
                cMin = c;
            }
        }
        int delta = cnt[v][ccur] - minCount;
        if (delta > 0) {
            bestColor[v] = cMin;
            curDelta[v] = delta;
        } else {
            bestColor[v] = ccur;
            curDelta[v] = 0;
        }
    }

    long long run(const chrono::steady_clock::time_point& deadline) {
        buildCounts();
        // Initialize improvements
        for (int v = 0; v < n; ++v) {
            recomputeVertex(v);
        }

        // Max-heap of (delta, vertex). We allow stale entries; verify upon pop.
        using PII = pair<int,int>;
        priority_queue<PII> pq;
        for (int v = 0; v < n; ++v) {
            if (curDelta[v] > 0) pq.emplace(curDelta[v], v);
        }

        int steps = 0;
        while (!pq.empty()) {
            if ((steps & 0x3FF) == 0) {
                if (chrono::steady_clock::now() > deadline) break;
            }
            auto [d, v] = pq.top(); pq.pop();
            if (d != curDelta[v] || d <= 0) continue;
            int oldc = col[v];
            int newc = bestColor[v];
            if (newc == oldc) continue;
            // Apply move
            // Update neighbor counts
            for (int u : g[v]) {
                cnt[u][oldc]--;
                cnt[u][newc]++;
            }
            // Update conflicts
            conflicts -= d;
            col[v] = newc;

            // Recompute v and neighbors
            recomputeVertex(v);
            if (curDelta[v] > 0) pq.emplace(curDelta[v], v);
            for (int u : g[v]) {
                recomputeVertex(u);
                if (curDelta[u] > 0) pq.emplace(curDelta[u], u);
            }
            ++steps;
        }
        return conflicts;
    }
};

vector<int> greedy_initial(const vector<vector<int>>& g, mt19937& rng) {
    int n = (int)g.size();
    vector<int> order(n);
    iota(order.begin(), order.end(), 0);
    vector<int> deg(n);
    for (int i = 0; i < n; ++i) deg[i] = (int)g[i].size();
    stable_sort(order.begin(), order.end(), [&](int a, int b){
        if (deg[a] != deg[b]) return deg[a] > deg[b];
        return a < b;
    });
    vector<int> col(n, -1);
    for (int v : order) {
        int cntc[3] = {0,0,0};
        for (int u : g[v]) {
            if (col[u] != -1) cntc[col[u]]++;
        }
        int minv = min(cntc[0], min(cntc[1], cntc[2]));
        vector<int> opts;
        for (int c = 0; c < 3; ++c) if (cntc[c] == minv) opts.push_back(c);
        int c = opts[rng() % opts.size()];
        col[v] = c;
    }
    return col;
}

vector<int> random_initial(int n, mt19937& rng) {
    vector<int> col(n);
    for (int i = 0; i < n; ++i) col[i] = (int)(rng() % 3);
    return col;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    vector<vector<int>> g(n);
    g.reserve(n);
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        g[u].push_back(v);
        g[v].push_back(u);
    }

    if (m == 0) {
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << 1;
        }
        cout << '\n';
        return 0;
    }

    Timer timer;
    auto seed = (uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count();
    mt19937 rng((uint32_t)(seed ^ (seed >> 32)));

    double time_budget_ms = 1900.0; // overall time budget
    auto deadline = timer.deadline(time_budget_ms);

    // Attempt 1: Greedy initialization + local search
    vector<int> best_col = greedy_initial(g, rng);
    {
        LocalSearch ls(g, best_col, rng);
        ls.run(deadline);
        best_col = ls.col;
    }

    // Optionally try random restarts while time remains
    // We'll attempt a few random restarts until time runs out
    int attempts = 0;
    while (chrono::steady_clock::now() < deadline) {
        vector<int> init = random_initial(n, rng);
        LocalSearch ls(g, init, rng);
        long long conf = ls.run(deadline);
        // Evaluate current best conflicts
        // Compute best conflicts to compare
        // Recompute conflicts for best_col
        // Since we don't store conflicts of best_col, compute quickly
        long long best_conf = 0;
        {
            vector<int>& col = best_col;
            // Count conflicts
            for (int v = 0; v < n; ++v) {
                for (int u : g[v]) if (u > v) {
                    if (col[u] == col[v]) best_conf++;
                }
            }
        }
        if (conf < best_conf) {
            best_col = ls.col;
        }
        attempts++;
        // Break if time very close to deadline
        if (chrono::steady_clock::now() > deadline) break;
    }

    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (best_col[i] + 1);
    }
    cout << '\n';
    return 0;
}