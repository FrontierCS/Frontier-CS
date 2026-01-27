#include <bits/stdc++.h>
using namespace std;

class FastScanner {
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

public:
    template <class T>
    bool readInt(T &out) {
        char c;
        do {
            c = readChar();
            if (!c) return false;
        } while (c <= ' ');

        bool neg = false;
        if (c == '-') {
            neg = true;
            c = readChar();
        }
        T val = 0;
        while (c > ' ') {
            val = val * 10 + (c - '0');
            c = readChar();
        }
        out = neg ? -val : val;
        return true;
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
    vector<int> deg;
    vector<vector<int>> adj;
};

static Graph readGraph(FastScanner &fs, int n, int m) {
    Graph g;
    g.n = n;
    g.deg.assign(n, 0);

    vector<int> U(m), V(m);
    for (int i = 0; i < m; i++) {
        int u, v;
        fs.readInt(u);
        fs.readInt(v);
        --u; --v;
        U[i] = u; V[i] = v;
        g.deg[u]++; g.deg[v]++;
    }

    g.adj.assign(n, {});
    for (int i = 0; i < n; i++) g.adj[i].reserve(g.deg[i]);
    for (int i = 0; i < m; i++) {
        int u = U[i], v = V[i];
        g.adj[u].push_back(v);
        g.adj[v].push_back(u);
    }
    return g;
}

struct Key {
    uint32_t c;
    uint32_t deg;
    uint64_t s1, s2, x;
    int idx; // 0..2n-1
    bool operator<(Key const& other) const {
        if (c != other.c) return c < other.c;
        if (deg != other.deg) return deg < other.deg;
        if (s1 != other.s1) return s1 < other.s1;
        if (s2 != other.s2) return s2 < other.s2;
        if (x != other.x) return x < other.x;
        return idx < other.idx;
    }
    bool sameSig(Key const& other) const {
        return c == other.c && deg == other.deg && s1 == other.s1 && s2 == other.s2 && x == other.x;
    }
};

int main() {
    FastScanner fs;
    int n, m;
    if (!fs.readInt(n)) return 0;
    fs.readInt(m);

    Graph g1 = readGraph(fs, n, m);
    Graph g2 = readGraph(fs, n, m);

    vector<uint32_t> col1(n), col2(n);

    // Initial colors: degree, compressed globally across both graphs.
    vector<int> allDeg;
    allDeg.reserve(2 * n);
    for (int i = 0; i < n; i++) allDeg.push_back(g1.deg[i]);
    for (int i = 0; i < n; i++) allDeg.push_back(g2.deg[i]);
    sort(allDeg.begin(), allDeg.end());
    allDeg.erase(unique(allDeg.begin(), allDeg.end()), allDeg.end());
    for (int i = 0; i < n; i++) col1[i] = (uint32_t)(lower_bound(allDeg.begin(), allDeg.end(), g1.deg[i]) - allDeg.begin());
    for (int i = 0; i < n; i++) col2[i] = (uint32_t)(lower_bound(allDeg.begin(), allDeg.end(), g2.deg[i]) - allDeg.begin());

    int iterations = 7;
    for (int it = 0; it < iterations; it++) {
        uint32_t maxC = 0;
        for (int i = 0; i < n; i++) maxC = max(maxC, col1[i]);
        for (int i = 0; i < n; i++) maxC = max(maxC, col2[i]);
        int C = (int)maxC + 1;

        vector<uint64_t> r1(C), r2(C), r3(C);
        uint64_t salt1 = 0x123456789abcdef0ULL ^ (uint64_t)it * 0x9e3779b97f4a7c15ULL;
        uint64_t salt2 = 0xfedcba9876543210ULL ^ (uint64_t)it * 0xbf58476d1ce4e5b9ULL;
        uint64_t salt3 = 0x0f0f0f0f0f0f0f0fULL ^ (uint64_t)it * 0x94d049bb133111ebULL;
        for (int c = 0; c < C; c++) {
            r1[c] = splitmix64((uint64_t)c + salt1);
            r2[c] = splitmix64((uint64_t)c + salt2);
            r3[c] = splitmix64((uint64_t)c + salt3);
        }

        vector<Key> keys;
        keys.reserve(2 * n);

        // G1
        for (int v = 0; v < n; v++) {
            uint64_t s1 = 0, s2 = 0, x = 0;
            for (int u : g1.adj[v]) {
                uint32_t cu = col1[u];
                s1 += r1[cu];
                s2 += r2[cu];
                x ^= r3[cu];
            }
            keys.push_back(Key{col1[v], (uint32_t)g1.deg[v], s1, s2, x, v});
        }

        // G2
        for (int v = 0; v < n; v++) {
            uint64_t s1 = 0, s2 = 0, x = 0;
            for (int u : g2.adj[v]) {
                uint32_t cu = col2[u];
                s1 += r1[cu];
                s2 += r2[cu];
                x ^= r3[cu];
            }
            keys.push_back(Key{col2[v], (uint32_t)g2.deg[v], s1, s2, x, n + v});
        }

        sort(keys.begin(), keys.end());

        vector<uint32_t> newCol1(n), newCol2(n);
        uint32_t newId = 0;
        for (int i = 0; i < (int)keys.size(); i++) {
            if (i > 0 && !keys[i].sameSig(keys[i - 1])) newId++;
            int idx = keys[i].idx;
            if (idx < n) newCol1[idx] = newId;
            else newCol2[idx - n] = newId;
        }

        if (newCol1 == col1 && newCol2 == col2) {
            col1.swap(newCol1);
            col2.swap(newCol2);
            break;
        }
        col1.swap(newCol1);
        col2.swap(newCol2);
    }

    uint32_t maxC = 0;
    for (int i = 0; i < n; i++) maxC = max(maxC, col1[i]);
    for (int i = 0; i < n; i++) maxC = max(maxC, col2[i]);
    int numColors = (int)maxC + 1;

    vector<vector<int>> group1(numColors), group2(numColors);
    for (int v = 0; v < n; v++) group1[col1[v]].push_back(v + 1);
    for (int v = 0; v < n; v++) group2[col2[v]].push_back(v + 1);

    vector<int> p(n + 1, 0);
    vector<char> usedG1(n + 1, 0);
    vector<int> unassigned;
    unassigned.reserve(n);

    for (int c = 0; c < numColors; c++) {
        auto &A = group2[c];
        auto &B = group1[c];
        int k = min((int)A.size(), (int)B.size());
        for (int i = 0; i < k; i++) {
            p[A[i]] = B[i];
            usedG1[B[i]] = 1;
        }
        for (int i = k; i < (int)A.size(); i++) unassigned.push_back(A[i]);
    }

    vector<int> avail;
    avail.reserve(n);
    for (int v = 1; v <= n; v++) if (!usedG1[v]) avail.push_back(v);

    for (int i = 0; i < (int)unassigned.size(); i++) {
        p[unassigned[i]] = avail[i];
    }

    // Output permutation: for vertex i of G2, mapped to p[i] in G1
    for (int i = 1; i <= n; i++) {
        if (i > 1) putchar_unlocked(' ');
        int x = p[i];
        // print int fast
        char s[16];
        int len = 0;
        while (x > 0) { s[len++] = char('0' + (x % 10)); x /= 10; }
        if (len == 0) s[len++] = '0';
        for (int j = len - 1; j >= 0; j--) putchar_unlocked(s[j]);
    }
    putchar_unlocked('\n');
    return 0;
}