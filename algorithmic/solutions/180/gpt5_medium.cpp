#include <bits/stdc++.h>
using namespace std;

static inline uint64_t splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ull;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ull;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebull;
    return x ^ (x >> 31);
}

struct Sig {
    uint32_t cur;
    uint32_t deg;
    uint64_t s1, s2, s3;
    bool operator<(Sig const& o) const {
        if (cur != o.cur) return cur < o.cur;
        if (deg != o.deg) return deg < o.deg;
        if (s1 != o.s1) return s1 < o.s1;
        if (s2 != o.s2) return s2 < o.s2;
        return s3 < o.s3;
    }
    bool operator==(Sig const& o) const {
        return cur==o.cur && deg==o.deg && s1==o.s1 && s2==o.s2 && s3==o.s3;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    long long m;
    if (!(cin >> n >> m)) {
        return 0;
    }
    vector<vector<int>> adj1(n), adj2(n);
    int B = (n + 63) >> 6;
    vector<vector<uint64_t>> bit1(n, vector<uint64_t>(B, 0));
    for (long long i = 0; i < m; ++i) {
        int u, v; cin >> u >> v; --u; --v;
        if (u == v) continue;
        adj1[u].push_back(v);
        adj1[v].push_back(u);
        bit1[u][v >> 6] |= (1ull << (v & 63));
        bit1[v][u >> 6] |= (1ull << (u & 63));
    }
    vector<pair<int,int>> edges2;
    edges2.reserve(m);
    for (long long i = 0; i < m; ++i) {
        int u, v; cin >> u >> v; --u; --v;
        if (u == v) continue;
        adj2[u].push_back(v);
        adj2[v].push_back(u);
        if (u < v) edges2.emplace_back(u, v);
        else edges2.emplace_back(v, u);
    }

    auto isEdge1 = [&](int a, int b)->int{
        return (bit1[a][b >> 6] >> (b & 63)) & 1ull;
    };

    vector<int> deg1(n), deg2(n);
    for (int i = 0; i < n; ++i) { deg1[i] = (int)adj1[i].size(); deg2[i] = (int)adj2[i].size(); }

    // Initial colors: degree
    vector<int> col1(n), col2(n);
    for (int i = 0; i < n; ++i) { col1[i] = deg1[i]; col2[i] = deg2[i]; }

    // 1-WL color refinement for a few iterations
    int iters = 4;
    for (int it = 0; it < iters; ++it) {
        vector<Sig> sig1(n), sig2(n);
        for (int i = 0; i < n; ++i) {
            uint64_t s1=1469598103934665603ull, s2=0x9e3779b97f4a7c15ull, s3=0;
            for (int nb : adj1[i]) {
                uint64_t c = (uint64_t)col1[nb] + 0x1000003dull;
                s1 += splitmix64(c ^ 0x9e3779b97f4a7c15ull);
                s2 ^= splitmix64(c + 0x243f6a8885a308d3ull);
                s3 += splitmix64(c * 0x100000001b3ull);
            }
            sig1[i] = Sig{(uint32_t)col1[i], (uint32_t)deg1[i], s1, s2, s3};
        }
        for (int i = 0; i < n; ++i) {
            uint64_t s1=1469598103934665603ull, s2=0x9e3779b97f4a7c15ull, s3=0;
            for (int nb : adj2[i]) {
                uint64_t c = (uint64_t)col2[nb] + 0x1000003dull;
                s1 += splitmix64(c ^ 0x9e3779b97f4a7c15ull);
                s2 ^= splitmix64(c + 0x243f6a8885a308d3ull);
                s3 += splitmix64(c * 0x100000001b3ull);
            }
            sig2[i] = Sig{(uint32_t)col2[i], (uint32_t)deg2[i], s1, s2, s3};
        }
        vector<pair<Sig, pair<int,int>>> comb;
        comb.reserve(2*n);
        for (int i = 0; i < n; ++i) comb.push_back({sig1[i], {0, i}});
        for (int i = 0; i < n; ++i) comb.push_back({sig2[i], {1, i}});
        sort(comb.begin(), comb.end(), [](auto &A, auto &B){
            if (A.first < B.first) return true;
            if (B.first < A.first) return false;
            return A.second < B.second;
        });
        int curId = 0;
        auto prevSig = comb[0].first;
        vector<int> ncol1(n), ncol2(n);
        for (size_t idx = 0; idx < comb.size(); ++idx) {
            if (idx == 0 || !(comb[idx].first == prevSig)) {
                if (idx != 0) curId++;
                prevSig = comb[idx].first;
            }
            if (comb[idx].second.first == 0) ncol1[comb[idx].second.second] = curId;
            else ncol2[comb[idx].second.second] = curId;
        }
        col1.swap(ncol1);
        col2.swap(ncol2);
    }

    // Additional features: sum of neighbor degrees, sum of neighbor colors
    vector<long long> sumDegNbr1(n,0), sumDegNbr2(n,0);
    vector<long long> sumColNbr1(n,0), sumColNbr2(n,0);
    for (int i = 0; i < n; ++i) {
        long long sD=0, sC=0;
        for (int nb : adj1[i]) { sD += deg1[nb]; sC += col1[nb]; }
        sumDegNbr1[i]=sD; sumColNbr1[i]=sC;
    }
    for (int i = 0; i < n; ++i) {
        long long sD=0, sC=0;
        for (int nb : adj2[i]) { sD += deg2[nb]; sC += col2[nb]; }
        sumDegNbr2[i]=sD; sumColNbr2[i]=sC;
    }

    // Prepare initial permutation by sorting with features
    struct NodeKey {
        int id;
        int color;
        int deg;
        long long sumDeg;
        long long sumCol;
    };
    vector<NodeKey> nodes1(n), nodes2(n);
    for (int i = 0; i < n; ++i) nodes1[i] = {i, col1[i], deg1[i], sumDegNbr1[i], sumColNbr1[i]};
    for (int i = 0; i < n; ++i) nodes2[i] = {i, col2[i], deg2[i], sumDegNbr2[i], sumColNbr2[i]};
    auto comp = [](const NodeKey& a, const NodeKey& b){
        if (a.color != b.color) return a.color < b.color;
        if (a.deg != b.deg) return a.deg > b.deg;
        if (a.sumDeg != b.sumDeg) return a.sumDeg > b.sumDeg;
        if (a.sumCol != b.sumCol) return a.sumCol > b.sumCol;
        return a.id < b.id;
    };
    sort(nodes1.begin(), nodes1.end(), comp);
    sort(nodes2.begin(), nodes2.end(), comp);

    vector<int> p(n), inv(n);
    for (int i = 0; i < n; ++i) {
        p[nodes2[i].id] = nodes1[i].id;
        inv[nodes1[i].id] = nodes2[i].id;
    }

    // Compute initial matched edges
    long long matched = 0;
    for (auto &e : edges2) {
        int u = e.first, v = e.second;
        if (isEdge1(p[u], p[v])) matched++;
    }

    // Local improvement by random swaps
    std::mt19937_64 rng(chrono::high_resolution_clock::now().time_since_epoch().count());
    double avgdeg = (n > 0 ? (double)(2.0 * m) / (double)n : 0.0);
    int MAX_ATTEMPTS = min(40000, max(5000, n * 15));
    for (int it = 0; it < MAX_ATTEMPTS; ++it) {
        int u = (int)(rng() % n);
        int v = (int)(rng() % n);
        if (u == v) continue;
        int du = (int)adj2[u].size();
        int dv = (int)adj2[v].size();
        if (du + dv > (int)(avgdeg * 6.0)) {
            if ((rng() & 3ULL) != 0ULL) continue; // skip heavy pairs most of the time
        }
        int a = p[u], b = p[v];
        if (a == b) continue;
        long long d = 0;
        // edges from u
        for (int x : adj2[u]) {
            if (x == v) continue;
            d += isEdge1(b, p[x]) - isEdge1(a, p[x]);
        }
        // edges from v
        for (int y : adj2[v]) {
            if (y == u) continue;
            d += isEdge1(a, p[y]) - isEdge1(b, p[y]);
        }
        if (d > 0) {
            swap(p[u], p[v]);
            // inv also updated, but only used if needed later
            inv[a] = v;
            inv[b] = u;
            matched += d;
        }
    }

    // Output permutation p (1-indexed)
    for (int i = 0; i < n; ++i) {
        if (i) cout << ' ';
        cout << (p[i] + 1);
    }
    cout << '\n';
    return 0;
}