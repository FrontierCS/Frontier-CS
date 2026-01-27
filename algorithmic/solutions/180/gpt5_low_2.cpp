#include <bits/stdc++.h>
using namespace std;

struct FastBitset {
    int n, W;
    vector<uint64_t> bits; // flattened n x W
    FastBitset() : n(0), W(0) {}
    FastBitset(int n_) { init(n_); }
    void init(int n_) {
        n = n_;
        W = (n + 63) >> 6;
        bits.assign((size_t)n * W, 0);
    }
    inline void setEdge(int u, int v) {
        // 0-based
        bits[(size_t)u * W + (v >> 6)] |= (1ULL << (v & 63));
        bits[(size_t)v * W + (u >> 6)] |= (1ULL << (u & 63));
    }
    inline bool test(int u, int v) const {
        return (bits[(size_t)u * W + (v >> 6)] >> (v & 63)) & 1ULL;
    }
};

static inline uint64_t splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) return 0;

    FastBitset A1(n);
    vector<int> deg1(n, 0), deg2(n, 0);
    vector<pair<int,int>> edges1, edges2;
    edges1.reserve(m);
    edges2.reserve(m);

    // Read G1
    for (int i = 0; i < m; ++i) {
        int u, v; cin >> u >> v; --u; --v;
        if (u == v) continue;
        if (u > v) swap(u, v);
        A1.setEdge(u, v);
        deg1[u]++; deg1[v]++;
        edges1.emplace_back(u, v);
    }

    // Build G2 adjacency
    vector<vector<int>> adj2(n);
    for (int i = 0; i < m; ++i) {
        int u, v; cin >> u >> v; --u; --v;
        if (u == v) continue;
        if (u > v) swap(u, v);
        edges2.emplace_back(u, v);
        adj2[u].push_back(v);
        adj2[v].push_back(u);
        deg2[u]++; deg2[v]++;
    }

    // Color refinement using degree-based invariant hashing
    auto refine_colors = [&](const vector<vector<int>>& adj, const vector<int>& deg) {
        vector<uint64_t> col(n);
        for (int i = 0; i < n; ++i) col[i] = splitmix64((uint64_t)deg[i] + 0x12345678ULL);
        for (int it = 0; it < 4; ++it) {
            vector<uint64_t> ncol(n);
            for (int v = 0; v < n; ++v) {
                uint64_t h1 = splitmix64(col[v] + 0x9e3779b185ebca87ULL);
                uint64_t h2 = 0, h3 = 0, h4 = 0;
                for (int u : adj[v]) {
                    uint64_t hc = splitmix64(col[u] + 0x9e3779b97f4a7c15ULL);
                    h2 += hc;
                    h3 ^= (hc + 0x9ddfea08eb382d69ULL) * 0xbf58476d1ce4e5b9ULL;
                    h4 += hc * hc + 0x94d049bb133111ebULL;
                }
                uint64_t h = h1;
                h ^= splitmix64(h2 + 0x517cc1b727220a95ULL);
                h ^= (splitmix64(h3 + 0x243f6a8885a308d3ULL) << 1);
                h ^= (splitmix64(h4 + 0x13198a2e03707344ULL) << 2);
                h ^= splitmix64((uint64_t)deg[v] + 0x769e3779b97f4a7cULL);
                ncol[v] = h;
            }
            col.swap(ncol);
        }
        return col;
    };

    vector<uint64_t> sig1 = refine_colors(*(new vector<vector<int>>(n)), deg1); // empty adj for G1? We need adjacency of G1 for refinement
    // We mistakenly created empty adj; fix by building adjacency list for G1 quickly from edges1
    vector<vector<int>> adj1(n);
    for (auto &e : edges1) {
        adj1[e.first].push_back(e.second);
        adj1[e.second].push_back(e.first);
    }
    sig1 = refine_colors(adj1, deg1);
    vector<uint64_t> sig2 = refine_colors(adj2, deg2);

    // Create ordering by signatures and degrees (and maybe index for tie-break)
    vector<int> order1(n), order2(n);
    iota(order1.begin(), order1.end(), 0);
    iota(order2.begin(), order2.end(), 0);

    auto key1 = [&](int v) {
        return tuple<uint64_t,int,int>(sig1[v], deg1[v], v);
    };
    auto key2 = [&](int v) {
        return tuple<uint64_t,int,int>(sig2[v], deg2[v], v);
    };
    stable_sort(order1.begin(), order1.end(), [&](int a, int b){
        if (sig1[a] != sig1[b]) return sig1[a] < sig1[b];
        if (deg1[a] != deg1[b]) return deg1[a] < deg1[b];
        return a < b;
    });
    stable_sort(order2.begin(), order2.end(), [&](int a, int b){
        if (sig2[a] != sig2[b]) return sig2[a] < sig2[b];
        if (deg2[a] != deg2[b]) return deg2[a] < deg2[b];
        return a < b;
    });

    // Initial permutation p: maps vertex i of G2 to vertex p[i] of G1
    vector<int> p(n, -1), invp(n, -1);
    for (int i = 0; i < n; ++i) {
        int v2 = order2[i];
        int v1 = order1[i];
        p[v2] = v1;
        invp[v1] = v2;
    }

    // Compute initial matched edges (count each edge once)
    long long matched = 0;
    for (auto &e : edges2) {
        int u = e.first, v = e.second;
        if (A1.test(p[u], p[v])) matched++;
    }

    // Local search: random pair swaps with delta evaluation
    std::mt19937_64 rng((uint64_t)chrono::high_resolution_clock::now().time_since_epoch().count());
    auto randint = [&](int l, int r)->int {
        uniform_int_distribution<int> dist(l, r);
        return dist(rng);
    };

    auto delta_swap = [&](int a, int b)->long long {
        if (a == b) return 0;
        int pa = p[a], pb = p[b];
        long long delta = 0;
        // For neighbors of a, count edge once using u<v rule
        for (int y : adj2[a]) {
            if (y == b) continue;
            int u = min(a, y), v = max(a, y);
            if (u != a) continue; // ensure counted once
            int py = p[y];
            int oldv = A1.test(pa, py) ? 1 : 0;
            int newv = A1.test(pb, py) ? 1 : 0;
            delta += (newv - oldv);
        }
        // For neighbors of b
        for (int y : adj2[b]) {
            if (y == a) continue;
            int u = min(b, y), v = max(b, y);
            if (u != b) continue;
            int py = p[y];
            int oldv = A1.test(pb, py) ? 1 : 0;
            int newv = A1.test(pa, py) ? 1 : 0;
            delta += (newv - oldv);
        }
        // Edge (a,b) if present contributes once; but since A1 is symmetric, swapping pa/pb does not change A1[pa][pb].
        // So no change needed.
        return delta;
    };

    // Time-bounded iterations
    auto start = chrono::steady_clock::now();
    const double TIME_LIMIT = 0.9; // seconds
    long long attempts = 0, accepted = 0;

    // Precompute an array of vertices for random sampling
    vector<int> vertices(n);
    iota(vertices.begin(), vertices.end(), 0);

    while (true) {
        attempts++;
        if ((attempts & 0x3FF) == 0) {
            auto now = chrono::steady_clock::now();
            double elapsed = chrono::duration<double>(now - start).count();
            if (elapsed > TIME_LIMIT) break;
        }
        int a = randint(0, n - 1);
        int b = randint(0, n - 1);
        if (a == b) continue;

        long long d = delta_swap(a, b);
        if (d > 0 || (d == 0 && (rng() & 1023ULL) == 0)) { // slight random walk to escape plateaus
            // apply swap
            swap(p[a], p[b]);
            matched += d;
            accepted++;
        }
    }

    // Output permutation (1-based indices)
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (p[i] + 1);
    }
    cout << '\n';
    return 0;
}