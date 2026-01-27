#include <bits/stdc++.h>
using namespace std;

static inline uint64_t now_millis() {
    using namespace std::chrono;
    return duration_cast<milliseconds>(steady_clock::now().time_since_epoch()).count();
}

vector<vector<int>> build_neighbors_from_bitset(int N, const vector<vector<uint64_t>>& adjBits) {
    int L = (N + 63) / 64;
    vector<vector<int>> neighbors(N);
    for (int u = 0; u < N; ++u) {
        for (int j = 0; j < L; ++j) {
            uint64_t w = adjBits[u][j];
            while (w) {
                int t = __builtin_ctzll(w);
                int v = j * 64 + t;
                if (v < N) neighbors[u].push_back(v);
                w &= w - 1;
            }
        }
    }
    return neighbors;
}

vector<char> greedy_min_degree_mis(const vector<vector<int>>& g, mt19937_64& rng) {
    int n = (int)g.size();
    vector<int> deg(n);
    for (int i = 0; i < n; ++i) deg[i] = (int)g[i].size();

    vector<vector<int>> buckets(n);
    vector<int> perm(n);
    iota(perm.begin(), perm.end(), 0);
    shuffle(perm.begin(), perm.end(), rng);
    for (int v : perm) {
        int d = deg[v];
        if (d < 0) d = 0;
        if (d >= n) d = n - 1;
        buckets[d].push_back(v);
    }

    vector<char> alive(n, 1);
    vector<int> selected;
    selected.reserve(n);
    int ptr = 0;
    int aliveCount = n;
    vector<int> toRemove;
    toRemove.reserve(n);

    while (aliveCount > 0) {
        while (ptr < n && buckets[ptr].empty()) ++ptr;
        if (ptr >= n) break;

        int chosen = -1;
        while (!buckets[ptr].empty()) {
            int v = buckets[ptr].back();
            buckets[ptr].pop_back();
            if (alive[v] && deg[v] == ptr) { chosen = v; break; }
        }
        if (chosen == -1) { ++ptr; continue; }

        int v = chosen;
        selected.push_back(v);

        toRemove.clear();
        if (alive[v]) { alive[v] = 0; --aliveCount; toRemove.push_back(v); }
        for (int u : g[v]) if (alive[u]) { alive[u] = 0; --aliveCount; toRemove.push_back(u); }

        int newMin = ptr;
        for (int u : toRemove) {
            for (int t : g[u]) if (alive[t]) {
                int nd = --deg[t];
                if (nd < 0) nd = 0;
                buckets[nd].push_back(t);
                if (nd < newMin) newMin = nd;
            }
        }
        if (newMin < ptr) ptr = newMin;
    }

    vector<char> inS(n, 0);
    for (int v : selected) inS[v] = 1;
    return inS;
}

void compute_conflict(const vector<vector<int>>& g, const vector<char>& inS, vector<int>& conflict) {
    int n = (int)g.size();
    conflict.assign(n, 0);
    for (int v = 0; v < n; ++v) if (inS[v]) {
        for (int u : g[v]) conflict[u] += 1;
    }
}

bool is_independent(const vector<vector<int>>& g, const vector<char>& inS) {
    int n = (int)g.size();
    for (int v = 0; v < n; ++v) if (inS[v]) {
        for (int u : g[v]) if (inS[u]) {
            return false;
        }
    }
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    long long M;
    if (!(cin >> N >> M)) {
        return 0;
    }

    int L = (N + 63) / 64;
    vector<vector<uint64_t>> adjBits(N, vector<uint64_t>(L, 0));

    for (long long i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        if (u == v || u < 0 || v < 0 || u >= N || v >= N) continue;
        adjBits[u][v >> 6] |= (1ULL << (v & 63));
        adjBits[v][u >> 6] |= (1ULL << (u & 63));
    }

    vector<vector<int>> g = build_neighbors_from_bitset(N, adjBits);

    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

    uint64_t start_ms = now_millis();
    const uint64_t TIME_LIMIT_MS = 1900; // 1.9s

    // Initial greedy solution
    vector<char> best = greedy_min_degree_mis(g, rng);
    int bestSize = 0;
    for (char c : best) if (c) ++bestSize;

    // Try a couple more greedy runs if time allows
    for (int attempt = 0; attempt < 2; ++attempt) {
        if (now_millis() - start_ms > TIME_LIMIT_MS * 3 / 10) break;
        vector<char> sol = greedy_min_degree_mis(g, rng);
        int sz = 0; for (char c : sol) if (c) ++sz;
        if (sz > bestSize) { best = sol; bestSize = sz; }
    }

    // Local search: iterated random kick + greedy fill
    vector<int> bestConflict;
    compute_conflict(g, best, bestConflict);

    // Iterate until time limit
    while (now_millis() - start_ms < TIME_LIMIT_MS) {
        vector<char> inS = best;
        vector<int> conflict = bestConflict;
        int curSize = bestSize;

        // Build current selected list
        vector<int> selected;
        selected.reserve(curSize);
        for (int i = 0; i < N; ++i) if (inS[i]) selected.push_back(i);
        if (selected.empty()) break;

        // Choose k vertices to remove
        int maxK = min(3, (int)selected.size());
        uniform_int_distribution<int> distK(1, maxK);
        int k = distK(rng);

        vector<int> zeros;
        zeros.reserve(N);

        for (int t = 0; t < k && !selected.empty(); ++t) {
            uniform_int_distribution<int> distIdx(0, (int)selected.size() - 1);
            int idx = distIdx(rng);
            int v = selected[idx];
            selected[idx] = selected.back();
            selected.pop_back();

            if (!inS[v]) { --t; continue; }
            inS[v] = 0;
            --curSize;
            for (int u : g[v]) {
                int old = conflict[u];
                conflict[u] = old - 1;
                if (!inS[u] && conflict[u] == 0) zeros.push_back(u);
            }
        }

        // Greedy fill with zero-conflict vertices
        while (!zeros.empty()) {
            int v = zeros.back();
            zeros.pop_back();
            if (inS[v] || conflict[v] != 0) continue;
            inS[v] = 1;
            ++curSize;
            for (int u : g[v]) {
                int old = conflict[u];
                conflict[u] = old + 1;
                // If some u became non-zero, it may remain in zeros list; will be skipped when popped.
            }
        }

        if (curSize > bestSize) {
            best = inS;
            bestConflict = conflict;
            bestSize = curSize;
        }

        if (now_millis() - start_ms > TIME_LIMIT_MS) break;
    }

    // Ensure validity; if somehow invalid, fix by simple greedy check
    if (!is_independent(g, best)) {
        vector<char> fix(N, 0);
        vector<char> used(N, 0);
        vector<int> order(N);
        iota(order.begin(), order.end(), 0);
        shuffle(order.begin(), order.end(), rng);
        for (int v : order) {
            bool ok = true;
            for (int u : g[v]) if (fix[u]) { ok = false; break; }
            if (ok) fix[v] = 1;
        }
        best = move(fix);
    }

    for (int i = 0; i < N; ++i) {
        cout << (best[i] ? 1 : 0) << '\n';
    }

    return 0;
}