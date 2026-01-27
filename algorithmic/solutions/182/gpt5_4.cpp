#include <bits/stdc++.h>
using namespace std;

struct Edge { int u, v; };
struct AdjEdge { int to, id; };

struct RNG {
    uint64_t s;
    RNG(uint64_t seed) { s = seed ? seed : 0x9e3779b97f4a7c15ULL; }
    inline uint64_t next() {
        s ^= s << 7;
        s ^= s >> 9;
        s ^= s << 8;
        return s;
    }
    inline uint32_t next_u32() { return (uint32_t)(next() >> 32); }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N; int M;
    if(!(cin >> N >> M)) {
        return 0;
    }
    vector<Edge> edges;
    edges.reserve(M);
    vector<vector<AdjEdge>> adj(N);
    for (int i = 0; i < M; ++i) {
        int u, v; cin >> u >> v; --u; --v;
        edges.push_back({u, v});
        adj[u].push_back({v, i});
        adj[v].push_back({u, i});
    }

    auto solveOnce = [&](uint64_t seed)->vector<unsigned char> {
        RNG rng(seed);
        vector<unsigned char> inCover(N, 0);
        vector<int> deg(N, 0);
        vector<unsigned char> removed(N, 0);
        // Initialize degrees for leaf elimination
        for (int i = 0; i < N; ++i) deg[i] = (int)adj[i].size();
        deque<int> leafq, zeroq;
        for (int i = 0; i < N; ++i) {
            if (deg[i] == 0) zeroq.push_back(i);
            else if (deg[i] == 1) leafq.push_back(i);
        }
        auto selectCover = [&](int u) {
            if (removed[u]) return;
            inCover[u] = 1;
            removed[u] = 1;
            for (auto &e : adj[u]) {
                int w = e.to;
                if (removed[w]) continue;
                deg[w]--;
                if (deg[w] == 1) leafq.push_back(w);
                else if (deg[w] == 0) zeroq.push_back(w);
            }
            deg[u] = 0;
        };
        auto removeIsolated = [&](int x) {
            if (!removed[x] && deg[x] == 0) {
                removed[x] = 1;
            }
        };
        while (!leafq.empty()) {
            int v = leafq.front(); leafq.pop_front();
            if (removed[v] || deg[v] != 1) continue;
            int u = -1;
            for (auto &e : adj[v]) {
                if (!removed[e.to]) { u = e.to; break; }
            }
            if (u == -1) { // treat as isolated
                zeroq.push_back(v);
            } else {
                selectCover(u);
            }
            while (!zeroq.empty()) {
                int z = zeroq.front(); zeroq.pop_front();
                if (!removed[z] && deg[z] == 0) removeIsolated(z);
            }
        }
        for (int i = 0; i < N; ++i) if (deg[i] == 0 && !removed[i]) removed[i] = 1;

        // Greedy hitting set on remaining uncovered edges
        vector<unsigned char> covered(M, 0);
        vector<int> resid(N, 0);
        vector<uint32_t> noise(N);
        for (int i = 0; i < N; ++i) noise[i] = rng.next_u32() & ((1u<<24)-1u);

        int uncovered = 0;
        for (int i = 0; i < M; ++i) {
            int a = edges[i].u, b = edges[i].v;
            if (inCover[a] || inCover[b]) {
                covered[i] = 1;
            } else {
                covered[i] = 0;
                resid[a]++; resid[b]++;
                uncovered++;
            }
        }

        struct HeapItem {
            long long key;
            int v;
            bool operator<(const HeapItem& other) const { return key < other.key; }
        };
        priority_queue<HeapItem> pq;
        auto make_key = [&](int v)->long long {
            return ((long long)resid[v] << 24) | (long long)noise[v];
        };
        for (int v = 0; v < N; ++v) {
            if (!inCover[v] && resid[v] > 0) {
                pq.push({make_key(v), v});
            }
        }
        auto selectVertex = [&](int v) {
            if (inCover[v]) return;
            inCover[v] = 1;
            // mark edges covered and update neighbors' residuals
            for (auto &ae : adj[v]) {
                int ei = ae.id;
                if (covered[ei]) continue;
                covered[ei] = 1;
                uncovered--;
                int w = (edges[ei].u == v ? edges[ei].v : edges[ei].u);
                if (!inCover[w]) {
                    resid[w]--;
                    if (resid[w] > 0) pq.push({make_key(w), w});
                }
            }
            resid[v] = 0;
        };

        while (uncovered > 0) {
            // Pop valid top
            int v = -1;
            while (!pq.empty()) {
                auto it = pq.top(); pq.pop();
                int x = it.v;
                if (inCover[x]) continue;
                if (resid[x] <= 0) continue;
                long long curKey = make_key(x);
                if (it.key != curKey) continue;
                v = x; break;
            }
            if (v == -1) {
                // Fallback: pick an endpoint of an uncovered edge with larger resid
                int idx = -1;
                for (int i = 0; i < M; ++i) { if (!covered[i]) { idx = i; break; } }
                if (idx == -1) break; // safety
                int a = edges[idx].u, b = edges[idx].v;
                if (inCover[a] && !inCover[b]) v = b;
                else if (inCover[b] && !inCover[a]) v = a;
                else if (!inCover[a] && !inCover[b]) v = (resid[a] >= resid[b] ? a : b);
                else continue; // both in cover? shouldn't happen if covered[idx]==false
            }
            selectVertex(v);
        }

        // Redundant removal: remove any selected vertex whose all neighbors are selected
        deque<int> cand;
        for (int v = 0; v < N; ++v) {
            if (!inCover[v]) continue;
            bool canRem = true;
            for (auto &ae : adj[v]) {
                if (!inCover[ae.to]) { canRem = false; break; }
            }
            if (canRem) cand.push_back(v);
        }
        while (!cand.empty()) {
            int v = cand.front(); cand.pop_front();
            if (!inCover[v]) continue;
            bool canRem = true;
            for (auto &ae : adj[v]) {
                if (!inCover[ae.to]) { canRem = false; break; }
            }
            if (canRem) {
                inCover[v] = 0;
                // No need to add neighbors back to queue since removal cannot create new removable vertices
            }
        }

        // Final safeguard: ensure coverage (should be true)
        for (int i = 0; i < M; ++i) {
            int a = edges[i].u, b = edges[i].v;
            if (!(inCover[a] || inCover[b])) {
                // Add one endpoint arbitrarily
                if (!inCover[a]) inCover[a] = 1;
                if (!inCover[b] && !(inCover[a] || inCover[b])) inCover[b] = 1;
            }
        }
        return inCover;
    };

    auto start = chrono::steady_clock::now();
    const double TIME_LIMIT = 1.85; // seconds
    vector<unsigned char> best;
    int bestK = INT_MAX;
    int runs = 0;
    uint64_t baseSeed = chrono::high_resolution_clock::now().time_since_epoch().count() ^ (uint64_t)(N * 1000003ull + M);
    while (true) {
        uint64_t seed = baseSeed ^ (uint64_t)runs * 0x9e3779b97f4a7c15ULL;
        auto sol = solveOnce(seed);
        int K = 0;
        for (int i = 0; i < N; ++i) if (sol[i]) ++K;
        // validate
        bool ok = true;
        for (int i = 0; i < M; ++i) {
            int a = edges[i].u, b = edges[i].v;
            if (!(sol[a] || sol[b])) { ok = false; break; }
        }
        if (ok && K < bestK) {
            bestK = K;
            best = move(sol);
        }
        runs++;
        auto now = chrono::steady_clock::now();
        double elapsed = chrono::duration<double>(now - start).count();
        if (elapsed > TIME_LIMIT) break;
        if (runs >= 3) break;
    }
    if (best.empty()) {
        best.assign(N, 1); // fallback
    }

    for (int i = 0; i < N; ++i) {
        cout << (best[i] ? 1 : 0) << '\n';
    }
    return 0;
}