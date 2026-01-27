#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr size_t BUFSIZE = 1 << 20;
    char buf[BUFSIZE];
    size_t idx = 0, size = 0;

    inline char readChar() {
        if (idx >= size) {
            size = fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }

    int nextInt() {
        char c;
        do { c = readChar(); } while (c <= ' ' && c != 0);
        int sgn = 1;
        if (c == '-') { sgn = -1; c = readChar(); }
        int x = 0;
        while (c > ' ') {
            x = x * 10 + (c - '0');
            c = readChar();
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

struct Graph {
    int n = 0;
    vector<int> start; // size n+1
    vector<int> adj;   // size 2m
    vector<int> deg;   // size n
};

static Graph buildGraph(int n, int m, FastScanner &fs) {
    Graph g;
    g.n = n;
    g.deg.assign(n, 0);
    vector<pair<int,int>> edges;
    edges.reserve(m);

    for (int i = 0; i < m; i++) {
        int u = fs.nextInt() - 1;
        int v = fs.nextInt() - 1;
        edges.push_back({u, v});
        g.deg[u]++; g.deg[v]++;
    }

    g.start.assign(n + 1, 0);
    for (int i = 0; i < n; i++) g.start[i + 1] = g.start[i] + g.deg[i];
    g.adj.assign(2LL * m, 0);
    vector<int> cur = g.start;

    for (auto [u, v] : edges) {
        g.adj[cur[u]++] = v;
        g.adj[cur[v]++] = u;
    }
    return g;
}

struct Sig {
    uint64_t a, b, c, d;
    bool operator<(Sig const& o) const {
        if (a != o.a) return a < o.a;
        if (b != o.b) return b < o.b;
        if (c != o.c) return c < o.c;
        return d < o.d;
    }
    bool operator==(Sig const& o) const {
        return a == o.a && b == o.b && c == o.c && d == o.d;
    }
};

static void compressColors(const vector<Sig> &sigAll, vector<int> &colorAll) {
    int N = (int)sigAll.size();
    vector<int> ord(N);
    iota(ord.begin(), ord.end(), 0);
    sort(ord.begin(), ord.end(), [&](int i, int j) { return sigAll[i] < sigAll[j]; });

    colorAll.assign(N, 0);
    int col = 0;
    colorAll[ord[0]] = 0;
    for (int k = 1; k < N; k++) {
        if (!(sigAll[ord[k]] == sigAll[ord[k-1]])) col++;
        colorAll[ord[k]] = col;
    }
}

static void wlRefineBoth(const Graph &g1, const Graph &g2, vector<int> &col1, vector<int> &col2, int iters = 5) {
    int n = g1.n;
    vector<Sig> sigAll(2 * n);
    vector<int> colorAll;

    // Initial: degree as signature (global)
    for (int v = 0; v < n; v++) sigAll[v] = Sig{(uint64_t)g1.deg[v], 0, 0, 0};
    for (int v = 0; v < n; v++) sigAll[n + v] = Sig{(uint64_t)g2.deg[v], 0, 0, 0};
    compressColors(sigAll, colorAll);

    col1.resize(n); col2.resize(n);
    for (int v = 0; v < n; v++) col1[v] = colorAll[v];
    for (int v = 0; v < n; v++) col2[v] = colorAll[n + v];

    for (int it = 0; it < iters; it++) {
        int C = 0;
        for (int v = 0; v < n; v++) C = max(C, col1[v] + 1);
        for (int v = 0; v < n; v++) C = max(C, col2[v] + 1);

        vector<uint64_t> r1(C), r2(C), r3(C);
        uint64_t base = 0x1234567890abcdefULL ^ (uint64_t)it * 0x9e3779b97f4a7c15ULL;
        for (int c = 0; c < C; c++) {
            r1[c] = splitmix64(base ^ (uint64_t)c * 0xD6E8FEB86659FD93ULL);
            r2[c] = splitmix64(base ^ (uint64_t)c * 0xA5A3564E27F57E6DULL);
            r3[c] = splitmix64(base ^ (uint64_t)c * 0x9E3779B185EBCA87ULL);
        }

        auto fillSigs = [&](const Graph &g, const vector<int> &col, int offset) {
            for (int v = 0; v < n; v++) {
                uint64_t s1 = 0, s2 = 0, x = 0;
                for (int ei = g.start[v]; ei < g.start[v + 1]; ei++) {
                    int u = g.adj[ei];
                    int c = col[u];
                    s1 += r1[c];
                    s2 += r2[c];
                    x ^= r3[c];
                }
                uint64_t a = (uint64_t)(uint32_t)col[v];
                a = (a << 32) | (uint64_t)(uint32_t)g.deg[v];
                sigAll[offset + v] = Sig{a, s1, s2, x};
            }
        };

        fillSigs(g1, col1, 0);
        fillSigs(g2, col2, n);
        compressColors(sigAll, colorAll);
        for (int v = 0; v < n; v++) col1[v] = colorAll[v];
        for (int v = 0; v < n; v++) col2[v] = colorAll[n + v];
    }
}

struct Key {
    int col;
    int deg;
    uint64_t sumDeg;
    uint64_t sumCol;
    uint64_t sumColHash;
    uint64_t x;
    int id;
};

static vector<Key> computeKeys(const Graph &g, const vector<int> &col) {
    int n = g.n;
    vector<Key> keys(n);
    for (int v = 0; v < n; v++) {
        uint64_t sd = 0, sc = 0, sch = 0, x = 0;
        for (int ei = g.start[v]; ei < g.start[v + 1]; ei++) {
            int u = g.adj[ei];
            sd += (uint64_t)g.deg[u];
            sc += (uint64_t)(col[u] + 1);
            uint64_t h = splitmix64((uint64_t)col[u] * 0x9e3779b97f4a7c15ULL + 0xBF58476D1CE4E5B9ULL);
            sch += h;
            x ^= splitmix64(h ^ 0x94D049BB133111EBULL);
        }
        keys[v] = Key{col[v], g.deg[v], sd, sc, sch, x, v};
    }
    return keys;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int n = fs.nextInt();
    int m = fs.nextInt();

    Graph g1 = buildGraph(n, m, fs);
    Graph g2 = buildGraph(n, m, fs);

    vector<int> col1, col2;
    wlRefineBoth(g1, g2, col1, col2, 6);

    vector<Key> k1 = computeKeys(g1, col1);
    vector<Key> k2 = computeKeys(g2, col2);

    vector<int> ord1(n), ord2(n);
    iota(ord1.begin(), ord1.end(), 0);
    iota(ord2.begin(), ord2.end(), 0);

    auto cmpByKey = [&](const vector<Key> &k) {
        return [&](int a, int b) {
            const Key &x = k[a], &y = k[b];
            if (x.col != y.col) return x.col < y.col;
            if (x.deg != y.deg) return x.deg < y.deg;
            if (x.sumDeg != y.sumDeg) return x.sumDeg < y.sumDeg;
            if (x.sumCol != y.sumCol) return x.sumCol < y.sumCol;
            if (x.sumColHash != y.sumColHash) return x.sumColHash < y.sumColHash;
            if (x.x != y.x) return x.x < y.x;
            return x.id < y.id;
        };
    };

    sort(ord1.begin(), ord1.end(), cmpByKey(k1));
    sort(ord2.begin(), ord2.end(), cmpByKey(k2));

    vector<int> p(n, 1);
    for (int i = 0; i < n; i++) {
        int v2 = ord2[i];
        int v1 = ord1[i];
        p[v2] = v1 + 1; // 1-based output
    }

    for (int i = 0; i < n; i++) {
        if (i) cout << ' ';
        cout << p[i];
    }
    cout << '\n';
    return 0;
}