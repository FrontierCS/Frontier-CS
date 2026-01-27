#include <bits/stdc++.h>
using namespace std;

using ull = unsigned long long;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, m;
    if (!(cin >> n >> m)) return 0;

    int W = (n + 63) >> 6;

    // Adjacency structures
    vector<vector<int>> adj1(n), adj2(n);
    vector<vector<ull>> bits1(n, vector<ull>(W, 0));

    auto setBit1 = [&](int u, int v){
        bits1[u][v>>6] |= (1ull << (v & 63));
    };
    auto getBit1 = [&](int u, int v)->int{
        return (bits1[u][v>>6] >> (v & 63)) & 1ull;
    };

    // Read G1
    for (int i = 0; i < m; ++i) {
        int u, v; cin >> u >> v; --u; --v;
        if (u == v) continue;
        adj1[u].push_back(v);
        adj1[v].push_back(u);
        setBit1(u, v);
        setBit1(v, u);
    }

    // Read G2
    for (int i = 0; i < m; ++i) {
        int u, v; cin >> u >> v; --u; --v;
        if (u == v) continue;
        adj2[u].push_back(v);
        adj2[v].push_back(u);
    }

    vector<int> deg1(n), deg2(n);
    for (int i = 0; i < n; ++i) { deg1[i] = (int)adj1[i].size(); deg2[i] = (int)adj2[i].size(); }

    // Joint Weisfeiler-Lehman refinement (colors aligned across graphs)
    vector<int> color1(n), color2(n);
    for (int i = 0; i < n; ++i) { color1[i] = deg1[i]; color2[i] = deg2[i]; }
    auto mix64 = [](uint64_t h, uint64_t k)->uint64_t{
        h ^= k + 0x9e3779b97f4a7c15ull + (h<<6) + (h>>2);
        return h;
    };

    int R = 4;
    for (int it = 0; it < R; ++it) {
        vector<uint64_t> sig1(n), sig2(n);
        // compute signatures
        for (int v = 0; v < n; ++v) {
            auto &nb = adj1[v];
            vector<int> tmp; tmp.reserve(nb.size());
            for (int u : nb) tmp.push_back(color1[u]);
            sort(tmp.begin(), tmp.end());
            uint64_t h = 1469598103934665603ull;
            h = mix64(h, (uint64_t)color1[v]*1315423911u + deg1[v]);
            for (int c : tmp) h = mix64(h, (uint64_t)c + 0x9e3779b97f4a7c15ull);
            sig1[v] = h;
        }
        for (int v = 0; v < n; ++v) {
            auto &nb = adj2[v];
            vector<int> tmp; tmp.reserve(nb.size());
            for (int u : nb) tmp.push_back(color2[u]);
            sort(tmp.begin(), tmp.end());
            uint64_t h = 1469598103934665603ull;
            h = mix64(h, (uint64_t)color2[v]*1315423911u + deg2[v]);
            for (int c : tmp) h = mix64(h, (uint64_t)c + 0x9e3779b97f4a7c15ull);
            sig2[v] = h;
        }
        // compress globally
        vector<pair<uint64_t,int>> all; all.reserve(2*n);
        for (int i = 0; i < n; ++i) all.emplace_back(sig1[i], -(i+1)); // negative mark graph1
        for (int i = 0; i < n; ++i) all.emplace_back(sig2[i], (i+1));  // positive mark graph2
        sort(all.begin(), all.end());
        int id = 0;
        uint64_t prev = 0xffffffffffffffffull;
        unordered_map<int,int> newc1, newc2; newc1.reserve(n*2); newc2.reserve(n*2);
        for (auto &pr : all) {
            if (pr.first != prev) { prev = pr.first; ++id; }
            int idx = pr.second;
            if (idx < 0) newc1[-idx - 1] = id;
            else newc2[idx - 1] = id;
        }
        bool changed = false;
        for (int i = 0; i < n; ++i) { if (color1[i] != newc1[i]) changed = true; color1[i] = newc1[i]; }
        for (int i = 0; i < n; ++i) { if (color2[i] != newc2[i]) changed = true; color2[i] = newc2[i]; }
        if (!changed) break;
    }

    // Build buckets by color id
    unordered_map<int, vector<int>> buck1, buck2;
    buck1.reserve(n*2); buck2.reserve(n*2);
    for (int i = 0; i < n; ++i) buck1[color1[i]].push_back(i);
    for (int i = 0; i < n; ++i) buck2[color2[i]].push_back(i);

    // Secondary features for ordering within buckets
    vector<long long> sdeg1(n,0), sdeg2(n,0);
    for (int i = 0; i < n; ++i) {
        long long s = 0;
        for (int u : adj1[i]) s += deg1[u];
        sdeg1[i] = s;
    }
    for (int i = 0; i < n; ++i) {
        long long s = 0;
        for (int u : adj2[i]) s += deg2[u];
        sdeg2[i] = s;
    }

    vector<int> p(n, -1); // p[u in G2] -> v in G1
    vector<char> used1(n, 0);

    vector<int> leftover2, leftover1;

    // For consistent key iteration, collect all color ids
    unordered_set<int> allcols; allcols.reserve(buck1.size()+buck2.size());
    for (auto &kv : buck1) allcols.insert(kv.first);
    for (auto &kv : buck2) allcols.insert(kv.first);

    for (int col : allcols) {
        auto &v1 = buck1[col];
        auto &v2 = buck2[col];
        vector<int> a = v1;
        vector<int> b = v2;
        auto comp1 = [&](int x, int y){
            if (deg1[x] != deg1[y]) return deg1[x] > deg1[y];
            if (sdeg1[x] != sdeg1[y]) return sdeg1[x] > sdeg1[y];
            return x < y;
        };
        auto comp2 = [&](int x, int y){
            if (deg2[x] != deg2[y]) return deg2[x] > deg2[y];
            if (sdeg2[x] != sdeg2[y]) return sdeg2[x] > sdeg2[y];
            return x < y;
        };
        sort(a.begin(), a.end(), comp1);
        sort(b.begin(), b.end(), comp2);
        int k = min((int)a.size(), (int)b.size());
        for (int i = 0; i < k; ++i) {
            p[b[i]] = a[i];
            used1[a[i]] = 1;
        }
        for (int i = k; i < (int)b.size(); ++i) leftover2.push_back(b[i]);
        for (int i = k; i < (int)a.size(); ++i) leftover1.push_back(a[i]);
    }

    // Map leftovers by degree descending
    auto compL1 = [&](int x, int y){
        if (deg1[x] != deg1[y]) return deg1[x] > deg1[y];
        if (sdeg1[x] != sdeg1[y]) return sdeg1[x] > sdeg1[y];
        return x < y;
    };
    auto compL2 = [&](int x, int y){
        if (deg2[x] != deg2[y]) return deg2[x] > deg2[y];
        if (sdeg2[x] != sdeg2[y]) return sdeg2[x] > sdeg2[y];
        return x < y;
    };
    sort(leftover1.begin(), leftover1.end(), compL1);
    sort(leftover2.begin(), leftover2.end(), compL2);

    int i1 = 0;
    for (int u : leftover2) {
        while (i1 < (int)leftover1.size() && used1[leftover1[i1]]) ++i1;
        int v = -1;
        if (i1 < (int)leftover1.size()) {
            v = leftover1[i1++];
        } else {
            // fallback: any unused
            for (int j = 0; j < n; ++j) if (!used1[j]) { v = j; break; }
        }
        if (v == -1) { // should not happen
            v = 0;
            while (used1[v]) ++v;
        }
        p[u] = v;
        used1[v] = 1;
    }
    // Ensure all assigned
    for (int u = 0; u < n; ++u) if (p[u] == -1) {
        int v = 0; while (v < n && used1[v]) ++v;
        if (v == n) v = 0;
        p[u] = v;
        if (v < n) used1[v] = 1;
    }

    // Local search improvement
    vector<int> c(n, 0);
    long long matched = 0;
    for (int u = 0; u < n; ++u) {
        int pu = p[u];
        int cnt = 0;
        for (int w : adj2[u]) {
            int pw = p[w];
            cnt += getBit1(pu, pw);
        }
        c[u] = cnt;
        matched += cnt;
    }
    matched /= 2;

    // Prepare buckets for swaps by final color
    unordered_map<int, vector<int>> buck2_final;
    buck2_final.reserve(n*2);
    for (int i = 0; i < n; ++i) buck2_final[color2[i]].push_back(i);

    // Random engine
    mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

    auto try_swap = [&](int a, int b)->long long {
        if (a == b) return 0;
        int pa = p[a], pb = p[b];
        if (pa == pb) return 0;
        long long delta = 0;
        // neighbors of a excluding b
        for (int x : adj2[a]) if (x != b) {
            int px = p[x];
            delta += getBit1(pb, px) - getBit1(pa, px);
        }
        // neighbors of b excluding a
        for (int x : adj2[b]) if (x != a) {
            int px = p[x];
            delta += getBit1(pa, px) - getBit1(pb, px);
        }
        return delta;
    };

    auto apply_swap = [&](int a, int b, long long delta){
        int pa = p[a], pb = p[b];
        // update c for neighbors
        for (int x : adj2[a]) if (x != b) {
            int px = p[x];
            c[x] += getBit1(pb, px) - getBit1(pa, px);
        }
        for (int x : adj2[b]) if (x != a) {
            int px = p[x];
            c[x] += getBit1(pa, px) - getBit1(pb, px);
        }
        // update c[a], c[b]
        int ca = 0, cb = 0;
        for (int x : adj2[a]) {
            int px = p[x];
            ca += getBit1(pb, px);
        }
        for (int x : adj2[b]) {
            int px = p[x];
            cb += getBit1(pa, px);
        }
        c[a] = ca;
        c[b] = cb;
        // swap mapping
        p[a] = pb; p[b] = pa;
        matched += delta;
    };

    auto time_start = chrono::steady_clock::now();
    auto time_limit = chrono::milliseconds(1800);

    // First, try improvements within same color buckets
    vector<int> cols_list;
    cols_list.reserve(buck2_final.size());
    for (auto &kv : buck2_final) cols_list.push_back(kv.first);

    // Attempt heuristic swaps
    int attempts = 0;
    const int MAX_ATTEMPTS = 200000;

    while (attempts < MAX_ATTEMPTS) {
        if (chrono::steady_clock::now() - time_start > time_limit) break;
        // Choose a strategy randomly
        int mode = uniform_int_distribution<int>(0, 2)(rng);
        int a, b;
        if (mode == 0 && !cols_list.empty()) {
            // pick a random bucket
            int col = cols_list[uniform_int_distribution<int>(0, (int)cols_list.size()-1)(rng)];
            auto &vec = buck2_final[col];
            if ((int)vec.size() < 2) { attempts++; continue; }
            a = vec[uniform_int_distribution<int>(0, (int)vec.size()-1)(rng)];
            b = vec[uniform_int_distribution<int>(0, (int)vec.size()-1)(rng)];
            if (a == b) continue;
        } else {
            a = uniform_int_distribution<int>(0, n-1)(rng);
            b = uniform_int_distribution<int>(0, n-1)(rng);
            if (a == b) continue;
        }
        long long delta = try_swap(a, b);
        if (delta > 0) {
            apply_swap(a, b, delta);
            // keep trying neighbors quickly
        }
        attempts++;
    }

    // Output permutation in 1-based indexing
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (p[i] + 1);
    }
    cout << '\n';
    return 0;
}