#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr size_t BUFSIZE = 1 << 20;
    int idx = 0, size = 0;
    char buf[BUFSIZE];

    inline char read() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }

    int nextInt() {
        char c;
        do c = read(); while (c <= ' ' && c);
        int sgn = 1;
        if (c == '-') { sgn = -1; c = read(); }
        int x = 0;
        while (c > ' ') {
            x = x * 10 + (c - '0');
            c = read();
        }
        return x * sgn;
    }
};

static inline uint64_t splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

static inline uint64_t rotl64(uint64_t x, int r) {
    return (x << r) | (x >> (64 - r));
}

struct Graph {
    int n;
    int m;
    vector<int> deg;
    vector<int> off;
    vector<int> adj; // size 2m
};

static Graph readGraphCSR(int n, int m, FastScanner& fs) {
    Graph g;
    g.n = n; g.m = m;
    g.deg.assign(n, 0);

    vector<int> U(m), V(m);
    for (int i = 0; i < m; i++) {
        int u = fs.nextInt() - 1;
        int v = fs.nextInt() - 1;
        U[i] = u; V[i] = v;
        g.deg[u]++; g.deg[v]++;
    }

    g.off.assign(n + 1, 0);
    for (int i = 0; i < n; i++) g.off[i + 1] = g.off[i] + g.deg[i];
    g.adj.assign(g.off[n], 0);
    vector<int> cur = g.off;

    for (int i = 0; i < m; i++) {
        int u = U[i], v = V[i];
        g.adj[cur[u]++] = v;
        g.adj[cur[v]++] = u;
    }

    return g;
}

static vector<uint64_t> neighborDegreeSum(const Graph& g) {
    vector<uint64_t> s(g.n, 0);
    for (int u = 0; u < g.n; u++) {
        uint64_t sum = 0;
        for (int ei = g.off[u]; ei < g.off[u + 1]; ei++) sum += (uint64_t)g.deg[g.adj[ei]];
        s[u] = sum;
    }
    return s;
}

static vector<uint64_t> WLlabels(const Graph& g, uint64_t seed, int iters) {
    vector<uint64_t> lab(g.n), nlab(g.n);
    for (int v = 0; v < g.n; v++) lab[v] = splitmix64(((uint64_t)g.deg[v] << 32) ^ (uint64_t)v ^ seed);

    for (int t = 0; t < iters; t++) {
        for (int v = 0; v < g.n; v++) {
            uint64_t sum = 0, sum2 = 0, x = 0;
            int d = g.deg[v];
            for (int ei = g.off[v]; ei < g.off[v + 1]; ei++) {
                int nb = g.adj[ei];
                uint64_t h = lab[nb];
                sum += h;
                sum2 += (h * h) + 0x9e3779b97f4a7c15ULL;
                x ^= rotl64(h ^ (uint64_t)nb * 0xD6E8FEB86659FD93ULL, nb & 63);
            }
            uint64_t z = lab[v];
            z ^= sum + 0xBF58476D1CE4E5B9ULL * (uint64_t)(d + 1);
            z ^= sum2 + 0x94D049BB133111EBULL * (uint64_t)(t + 1);
            z ^= x + seed;
            nlab[v] = splitmix64(z);
        }
        lab.swap(nlab);
    }
    return lab;
}

struct Key {
    int deg;
    uint64_t nbrSum;
    uint64_t l1, l2;
    int id;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int n = fs.nextInt();
    int m = fs.nextInt();

    Graph g1 = readGraphCSR(n, m, fs);
    Graph g2 = readGraphCSR(n, m, fs);

    vector<uint64_t> nds1 = neighborDegreeSum(g1);
    vector<uint64_t> nds2 = neighborDegreeSum(g2);

    const int iters = 7;
    const uint64_t seedA = 0x123456789ABCDEF0ULL;
    const uint64_t seedB = 0x0FEDCBA987654321ULL;

    vector<uint64_t> l1a = WLlabels(g1, seedA, iters);
    vector<uint64_t> l1b = WLlabels(g1, seedB, iters);
    vector<uint64_t> l2a = WLlabels(g2, seedA, iters);
    vector<uint64_t> l2b = WLlabels(g2, seedB, iters);

    vector<Key> k1(n), k2(n);
    for (int i = 0; i < n; i++) {
        k1[i] = Key{g1.deg[i], nds1[i], l1a[i], l1b[i], i};
        k2[i] = Key{g2.deg[i], nds2[i], l2a[i], l2b[i], i};
    }

    auto cmp = [](const Key& a, const Key& b) {
        if (a.deg != b.deg) return a.deg > b.deg;
        if (a.nbrSum != b.nbrSum) return a.nbrSum > b.nbrSum;
        if (a.l1 != b.l1) return a.l1 < b.l1;
        if (a.l2 != b.l2) return a.l2 < b.l2;
        return a.id < b.id;
    };

    sort(k1.begin(), k1.end(), cmp);
    sort(k2.begin(), k2.end(), cmp);

    vector<int> map2to1(n, -1);
    for (int i = 0; i < n; i++) map2to1[k2[i].id] = k1[i].id;

    string out;
    out.reserve(n * 8);
    for (int i = 0; i < n; i++) {
        if (i) out.push_back(' ');
        out += to_string(map2to1[i] + 1);
    }
    out.push_back('\n');
    cout << out;
    return 0;
}