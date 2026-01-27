#include <bits/stdc++.h>
using namespace std;

const int MAXN = 2000;
bitset<MAXN> g1[MAXN];

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    vector<vector<int>> adj1(n), adj2(n);
    vector<int> deg1(n, 0), deg2(n, 0);
    vector<pair<int,int>> edges2;
    edges2.reserve(m);

    // Read first graph (G1)
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        adj1[u].push_back(v);
        adj1[v].push_back(u);
        deg1[u]++; deg1[v]++;
        g1[u].set(v);
        g1[v].set(u);
    }

    // Read second graph (G2)
    for (int i = 0; i < m; ++i) {
        int u, v;
        cin >> u >> v;
        --u; --v;
        adj2[u].push_back(v);
        adj2[v].push_back(u);
        deg2[u]++; deg2[v]++;
        edges2.push_back({u, v});
    }

    // Initial colors by degree (compressed over both graphs)
    vector<int> color1(n), color2(n);
    vector<int> allDeg;
    allDeg.reserve(2 * n);
    for (int i = 0; i < n; ++i) {
        allDeg.push_back(deg1[i]);
        allDeg.push_back(deg2[i]);
    }
    sort(allDeg.begin(), allDeg.end());
    allDeg.erase(unique(allDeg.begin(), allDeg.end()), allDeg.end());
    auto degToColor = [&](int d) -> int {
        return int(lower_bound(allDeg.begin(), allDeg.end(), d) - allDeg.begin());
    };
    for (int i = 0; i < n; ++i) {
        color1[i] = degToColor(deg1[i]);
        color2[i] = degToColor(deg2[i]);
    }

    // Random numbers for colors
    int maxColorsPossible = 2 * n + 5;
    vector<uint64_t> randColor(maxColorsPossible);
    uint64_t seed = 123456789123456789ULL;
    auto splitmix64 = [&](uint64_t &x) -> uint64_t {
        uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    };
    for (int i = 0; i < maxColorsPossible; ++i) {
        randColor[i] = splitmix64(seed);
    }

    struct WLItem {
        int oldColor;
        uint64_t sum;
        uint64_t xr;
        int degree;
        int graph;  // 0 = G1, 1 = G2
        int vertex;
    };

    // Weisfeiler-Lehman refinement
    const int MAX_ITERS = 5;
    for (int it = 0; it < MAX_ITERS; ++it) {
        vector<WLItem> items;
        items.reserve(2 * n);

        // Graph 1
        for (int v = 0; v < n; ++v) {
            uint64_t sum = 0, xr = 0;
            for (int u : adj1[v]) {
                int c = color1[u];
                uint64_t r = randColor[c];
                sum += r;
                xr ^= r;
            }
            items.push_back({color1[v], sum, xr, deg1[v], 0, v});
        }

        // Graph 2
        for (int v = 0; v < n; ++v) {
            uint64_t sum = 0, xr = 0;
            for (int u : adj2[v]) {
                int c = color2[u];
                uint64_t r = randColor[c];
                sum += r;
                xr ^= r;
            }
            items.push_back({color2[v], sum, xr, deg2[v], 1, v});
        }

        sort(items.begin(), items.end(), [](const WLItem &a, const WLItem &b) {
            if (a.oldColor != b.oldColor) return a.oldColor < b.oldColor;
            if (a.sum != b.sum) return a.sum < b.sum;
            if (a.xr != b.xr) return a.xr < b.xr;
            if (a.degree != b.degree) return a.degree < b.degree;
            if (a.graph != b.graph) return a.graph < b.graph;
            return a.vertex < b.vertex;
        });

        vector<int> newColor1(n), newColor2(n);
        int currentColorId = 0;
        WLItem prev = items[0];
        if (items[0].graph == 0) newColor1[items[0].vertex] = currentColorId;
        else newColor2[items[0].vertex] = currentColorId;

        for (size_t i = 1; i < items.size(); ++i) {
            WLItem &cur = items[i];
            if (cur.oldColor != prev.oldColor ||
                cur.sum != prev.sum ||
                cur.xr != prev.xr ||
                cur.degree != prev.degree) {
                ++currentColorId;
            }
            if (cur.graph == 0) newColor1[cur.vertex] = currentColorId;
            else newColor2[cur.vertex] = currentColorId;
            prev = cur;
        }

        bool changed = false;
        for (int i = 0; i < n; ++i) {
            if (newColor1[i] != color1[i]) { changed = true; break; }
            if (newColor2[i] != color2[i]) { changed = true; break; }
        }
        color1.swap(newColor1);
        color2.swap(newColor2);
        if (!changed) break;
    }

    // Compute hash features for final matching
    const uint64_t CONST1 = 0x9e3779b97f4a7c15ULL;
    vector<uint64_t> hash1(n), hash2(n);

    for (int v = 0; v < n; ++v) {
        uint64_t sum = 0, xr = 0;
        for (int u : adj1[v]) {
            int c = color1[u];
            uint64_t r = randColor[c];
            sum += r;
            xr ^= r;
        }
        hash1[v] = sum ^ (xr * CONST1);
    }
    for (int v = 0; v < n; ++v) {
        uint64_t sum = 0, xr = 0;
        for (int u : adj2[v]) {
            int c = color2[u];
            uint64_t r = randColor[c];
            sum += r;
            xr ^= r;
        }
        hash2[v] = sum ^ (xr * CONST1);
    }

    struct NodeFeat {
        int idx;
        int color;
        int deg;
        uint64_t hash;
    };

    vector<NodeFeat> nodes1(n), nodes2(n);
    for (int i = 0; i < n; ++i) {
        nodes1[i] = {i, color1[i], deg1[i], hash1[i]};
        nodes2[i] = {i, color2[i], deg2[i], hash2[i]};
    }

    auto cmpNode = [](const NodeFeat &a, const NodeFeat &b) {
        if (a.color != b.color) return a.color < b.color;
        if (a.deg != b.deg) return a.deg > b.deg;  // high degree first
        if (a.hash != b.hash) return a.hash < b.hash;
        return a.idx < b.idx;
    };
    sort(nodes1.begin(), nodes1.end(), cmpNode);
    sort(nodes2.begin(), nodes2.end(), cmpNode);

    // Initial permutation p: G2 vertex -> G1 vertex
    vector<int> p(n);
    for (int i = 0; i < n; ++i) {
        int v2 = nodes2[i].idx;
        int v1 = nodes1[i].idx;
        p[v2] = v1;
    }

    // Initial matched edges count
    long long matched = 0;
    for (auto &e : edges2) {
        int u = e.first, v = e.second;
        if (g1[p[u]].test(p[v])) matched++;
    }

    // Local search: random swaps that improve matched edge count
    std::mt19937_64 rng(splitmix64(seed));
    int maxIter = min(20000, 100 * n);

    auto calc_delta = [&](int a, int b) -> long long {
        if (a == b) return 0;
        int pa = p[a];
        int pb = p[b];
        if (pa == pb) return 0;
        long long delta = 0;

        // Edges incident to a
        for (int u : adj2[a]) {
            if (u == b) continue;  // edge (a,b) unchanged
            int pu = p[u];
            bool before = g1[pa].test(pu);
            bool after  = g1[pb].test(pu);
            if (after && !before) delta++;
            else if (!after && before) delta--;
        }
        // Edges incident to b
        for (int v : adj2[b]) {
            if (v == a) continue;
            int pv = p[v];
            bool before = g1[pb].test(pv);
            bool after  = g1[pa].test(pv);
            if (after && !before) delta++;
            else if (!after && before) delta--;
        }
        return delta;
    };

    for (int iter = 0; iter < maxIter; ++iter) {
        int a = int(rng() % n);
        int b = int(rng() % n);
        if (a == b) continue;
        long long delta = calc_delta(a, b);
        if (delta > 0) {
            matched += delta;
            swap(p[a], p[b]);
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