#include <bits/stdc++.h>
using namespace std;

static inline uint64_t splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9;
    x = (x ^ (x >> 27)) * 0x94d049bb133111eb;
    return x ^ (x >> 31);
}
struct FastRNG {
    uint64_t seed;
    FastRNG() {
        uint64_t t = chrono::high_resolution_clock::now().time_since_epoch().count();
        seed = splitmix64(t ^ (t >> 7) ^ (t << 3));
    }
    inline uint32_t next() {
        seed = splitmix64(seed + 0x9e3779b97f4a7c15ULL);
        return (uint32_t)(seed & 0xffffffffu);
    }
    inline uint64_t next64() {
        seed = splitmix64(seed + 0x9e3779b97f4a7c15ULL);
        return seed;
    }
    template<typename It>
    void shuffle(It first, It last) {
        if (first == last) return;
        size_t n = last - first;
        for (size_t i = n - 1; i > 0; --i) {
            size_t j = next() % (i + 1);
            if (i != j) swap(*(first + i), *(first + j));
        }
    }
} rng;

static inline void deduplicate_graph(vector<vector<int>>& g) {
    int n = (int)g.size();
    for (int i = 0; i < n; ++i) {
        auto &adj = g[i];
        sort(adj.begin(), adj.end());
        adj.erase(unique(adj.begin(), adj.end()), adj.end());
    }
}

// Greedy selection based on a static order
static vector<int> greedy_by_order(const vector<vector<int>>& g, const vector<int>& order) {
    int n = (int)g.size();
    vector<char> banned(n, 0);
    vector<int> sel(n, 0);
    for (int v : order) {
        if (!banned[v]) {
            sel[v] = 1;
            banned[v] = 1;
            for (int u : g[v]) banned[u] = 1;
        }
    }
    return sel;
}

// Min-degree dynamic greedy using bucket structure (near O(M))
static vector<int> min_degree_bucket(const vector<vector<int>>& g, bool randomized) {
    int n = (int)g.size();
    vector<int> deg(n);
    int maxDeg = 0;
    for (int i = 0; i < n; ++i) {
        deg[i] = (int)g[i].size();
        if (deg[i] > maxDeg) maxDeg = deg[i];
    }
    vector<vector<int>> buckets(maxDeg + 1);
    buckets.reserve(maxDeg + 1);
    for (int i = 0; i < n; ++i) buckets[deg[i]].push_back(i);

    vector<char> removed(n, 0);
    vector<int> sel(n, 0);
    int remaining = n;
    int curMin = 0;

    auto get_next = [&](int& v_out) -> bool {
        while (curMin <= maxDeg) {
            auto &B = buckets[curMin];
            while (!B.empty()) {
                int pos;
                if (randomized) pos = (int)(rng.next() % B.size());
                else pos = (int)B.size() - 1;
                int v = B[pos];
                // remove from bucket
                B[pos] = B.back();
                B.pop_back();
                if (removed[v]) continue;
                if (deg[v] != curMin) continue;
                v_out = v;
                return true;
            }
            ++curMin;
        }
        return false;
    };

    vector<int> toRemove;
    toRemove.reserve(128);

    while (remaining > 0) {
        int v;
        if (!get_next(v)) break;
        sel[v] = 1;
        toRemove.clear();
        toRemove.push_back(v);
        for (int u : g[v]) if (!removed[u]) toRemove.push_back(u);
        // mark all to be removed first
        for (int r : toRemove) {
            if (!removed[r]) {
                removed[r] = 1;
                --remaining;
            }
        }
        // update degrees of neighbors of removed nodes
        for (int r : toRemove) {
            for (int w : g[r]) {
                if (!removed[w]) {
                    int nd = --deg[w];
                    if (nd < 0) nd = 0;
                    if (nd <= curMin) curMin = nd;
                    buckets[nd].push_back(w);
                }
            }
        }
    }
    return sel;
}

static inline bool is_independent(const vector<vector<int>>& g, const vector<int>& sel) {
    int n = (int)g.size();
    for (int v = 0; v < n; ++v) if (sel[v]) {
        for (int u : g[v]) {
            if (u > v && sel[u]) return false;
        }
    }
    return true;
}

static vector<int> repair_and_complete(const vector<vector<int>>& g, vector<int> sel) {
    int n = (int)g.size();
    vector<int> deg(n);
    for (int i = 0; i < n; ++i) deg[i] = (int)g[i].size();

    // Repair independence, if needed
    // We'll ensure no edge has both endpoints selected
    // For each edge (v,u) with v<u and both selected, deselect the higher-degree or higher-index vertex.
    for (int v = 0; v < n; ++v) if (sel[v]) {
        for (int u : g[v]) if (u > v && sel[u]) {
            if (deg[v] > deg[u]) sel[v] = 0;
            else if (deg[v] < deg[u]) sel[u] = 0;
            else {
                // tie-break by id
                if (v > u) sel[v] = 0;
                else sel[u] = 0;
            }
        }
    }

    // Complete to a maximal independent set
    vector<char> banned(n, 0);
    for (int v = 0; v < n; ++v) if (sel[v]) {
        banned[v] = 1;
        for (int u : g[v]) banned[u] = 1;
    }
    for (int v = 0; v < n; ++v) if (!banned[v]) {
        sel[v] = 1;
        banned[v] = 1;
        for (int u : g[v]) banned[u] = 1;
    }
    return sel;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) {
        return 0;
    }
    vector<vector<int>> g(N);
    g.reserve(N);
    for (int i = 0; i < M; ++i) {
        int u, v; cin >> u >> v;
        --u; --v;
        if (u == v) continue;
        g[u].push_back(v);
        g[v].push_back(u);
    }
    deduplicate_graph(g);

    vector<int> degree(N);
    for (int i = 0; i < N; ++i) degree[i] = (int)g[i].size();

    auto start = chrono::high_resolution_clock::now();
    auto elapsed_ms = [&]() -> double {
        auto now = chrono::high_resolution_clock::now();
        return chrono::duration<double, std::milli>(now - start).count();
    };

    const double TIME_LIMIT_MS = 1800.0;

    auto evaluate = [&](vector<int> sel) -> pair<int, vector<int>> {
        if (!is_independent(g, sel)) {
            sel = repair_and_complete(g, sel);
        } else {
            // ensure maximal completion (in case the heuristic didn't produce a maximal set)
            sel = repair_and_complete(g, sel);
        }
        int K = 0;
        for (int x : sel) K += x;
        return {K, move(sel)};
    };

    int bestK = -1;
    vector<int> bestSel(N, 0);

    // Heuristic 1: dynamic min-degree bucket (randomized tie-breaking)
    {
        vector<int> cand = min_degree_bucket(g, true);
        auto res = evaluate(move(cand));
        if (res.first > bestK) { bestK = res.first; bestSel = move(res.second); }
    }

    // Heuristic 2: static ascending degree
    {
        vector<int> order(N);
        iota(order.begin(), order.end(), 0);
        stable_sort(order.begin(), order.end(), [&](int a, int b) {
            if (degree[a] != degree[b]) return degree[a] < degree[b];
            return a < b;
        });
        vector<int> cand = greedy_by_order(g, order);
        auto res = evaluate(move(cand));
        if (res.first > bestK) { bestK = res.first; bestSel = move(res.second); }
    }

    // Heuristic 3: static ascending degree with random tie-breaking
    if (elapsed_ms() < TIME_LIMIT_MS) {
        vector<pair<pair<int, uint32_t>, int>> arr;
        arr.reserve(N);
        for (int i = 0; i < N; ++i) arr.push_back({{degree[i], rng.next()}, i});
        sort(arr.begin(), arr.end(), [&](auto &A, auto &B){
            if (A.first.first != B.first.first) return A.first.first < B.first.first;
            return A.first.second < B.first.second;
        });
        vector<int> order(N);
        for (int i = 0; i < N; ++i) order[i] = arr[i].second;
        vector<int> cand = greedy_by_order(g, order);
        auto res = evaluate(move(cand));
        if (res.first > bestK) { bestK = res.first; bestSel = move(res.second); }
    }

    // Heuristic 4+: multiple random order runs within time
    int randomRuns = 3;
    for (int r = 0; r < randomRuns; ++r) {
        if (elapsed_ms() > TIME_LIMIT_MS) break;
        vector<int> order(N);
        iota(order.begin(), order.end(), 0);
        rng.shuffle(order.begin(), order.end());
        vector<int> cand = greedy_by_order(g, order);
        auto res = evaluate(move(cand));
        if (res.first > bestK) { bestK = res.first; bestSel = move(res.second); }
    }

    // Output final solution
    for (int i = 0; i < N; ++i) {
        cout << (bestSel[i] ? 1 : 0) << '\n';
    }
    return 0;
}