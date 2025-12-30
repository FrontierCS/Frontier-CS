#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr size_t BUFSIZE = 1 << 20;
    unsigned char buf[BUFSIZE];
    size_t idx = 0, size = 0;

    inline unsigned char read() {
        if (idx >= size) {
            size = fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }

    template <class T>
    bool readInt(T &out) {
        unsigned char c;
        do {
            c = read();
            if (!c) return false;
        } while (c <= ' ');

        bool neg = false;
        if (c == '-') {
            neg = true;
            c = read();
        }

        T val = 0;
        while (c > ' ') {
            val = val * 10 + (c - '0');
            c = read();
        }
        out = neg ? -val : val;
        return true;
    }
};

struct FastWriter {
    static constexpr size_t BUFSIZE = 1 << 20;
    char buf[BUFSIZE];
    size_t idx = 0;

    ~FastWriter() { flush(); }

    inline void flush() {
        if (idx) {
            fwrite(buf, 1, idx, stdout);
            idx = 0;
        }
    }

    inline void pushChar(char c) {
        if (idx >= BUFSIZE) flush();
        buf[idx++] = c;
    }

    template <class T>
    inline void writeInt(T x, char after = '\n') {
        if (x == 0) {
            pushChar('0');
            if (after) pushChar(after);
            return;
        }
        if (x < 0) {
            pushChar('-');
            x = -x;
        }
        char s[32];
        int n = 0;
        while (x > 0) {
            s[n++] = char('0' + (x % 10));
            x /= 10;
        }
        while (n--) pushChar(s[n]);
        if (after) pushChar(after);
    }
};

struct SplitMix64 {
    uint64_t x;
    explicit SplitMix64(uint64_t seed = 0x123456789ULL) : x(seed) {}
    inline uint64_t next() {
        uint64_t z = (x += 0x9e3779b97f4a7c15ULL);
        z = (z ^ (z >> 30)) * 0xbf58476d1ce4e5b9ULL;
        z = (z ^ (z >> 27)) * 0x94d049bb133111ebULL;
        return z ^ (z >> 31);
    }
    inline uint64_t operator()() { return next(); }
};

static inline void fisherYatesShuffle(vector<int> &a, SplitMix64 &rng) {
    for (int i = (int)a.size() - 1; i > 0; --i) {
        int j = (int)(rng.next() % (uint64_t)(i + 1));
        std::swap(a[i], a[j]);
    }
}

int main() {
    FastScanner fs;
    FastWriter fw;

    int n, m;
    if (!fs.readInt(n)) return 0;
    fs.readInt(m);

    for (int i = 0; i < 10; i++) {
        int tmp;
        fs.readInt(tmp);
    }

    vector<int> U(m), V(m);
    vector<int> outdeg(n + 1, 0), indeg(n + 1, 0);

    for (int i = 0; i < m; i++) {
        int u, v;
        fs.readInt(u);
        fs.readInt(v);
        U[i] = u;
        V[i] = v;
        outdeg[u]++;
        indeg[v]++;
    }

    vector<int> key(m);
    for (int i = 0; i < m; i++) key[i] = outdeg[U[i]] + indeg[V[i]];

    vector<int> ordAsc(m), ordDesc(m), ordRand(m);
    iota(ordAsc.begin(), ordAsc.end(), 0);
    iota(ordRand.begin(), ordRand.end(), 0);

    sort(ordAsc.begin(), ordAsc.end(), [&](int a, int b) {
        int ka = key[a], kb = key[b];
        if (ka != kb) return ka < kb;
        return a < b;
    });
    ordDesc = ordAsc;
    reverse(ordDesc.begin(), ordDesc.end());

    vector<int> succ(n + 1), pred(n + 1), parent(n + 1), sz(n + 1);

    auto runAttempt = [&](const vector<int> &order) -> vector<int> {
        fill(succ.begin(), succ.end(), 0);
        fill(pred.begin(), pred.end(), 0);
        for (int i = 1; i <= n; i++) {
            parent[i] = i;
            sz[i] = 1;
        }

        auto findp = [&](int x) {
            while (parent[x] != x) {
                parent[x] = parent[parent[x]];
                x = parent[x];
            }
            return x;
        };

        for (int id : order) {
            int u = U[id], v = V[id];
            if (succ[u] == 0 && pred[v] == 0) {
                int ru = findp(u), rv = findp(v);
                if (ru != rv) {
                    succ[u] = v;
                    pred[v] = u;
                    if (sz[ru] < sz[rv]) swap(ru, rv);
                    parent[rv] = ru;
                    sz[ru] += sz[rv];
                }
            }
        }

        int bestHead = 1, bestLen = 0;
        for (int v = 1; v <= n; v++) {
            if (pred[v] == 0) {
                int len = 0;
                int cur = v;
                while (cur) {
                    len++;
                    cur = succ[cur];
                }
                if (len > bestLen) {
                    bestLen = len;
                    bestHead = v;
                }
            }
        }

        vector<int> path;
        path.reserve(bestLen);
        int cur = bestHead;
        while (cur) {
            path.push_back(cur);
            cur = succ[cur];
        }
        return path;
    };

    SplitMix64 rng(0xC0FFEE123456789ULL);

    vector<int> bestPath;

    // Fixed heuristic attempts
    {
        auto p = runAttempt(ordAsc);
        bestPath = std::move(p);
        if ((int)bestPath.size() == n) goto OUTPUT;
    }
    {
        auto p = runAttempt(ordDesc);
        if (p.size() > bestPath.size()) bestPath = std::move(p);
        if ((int)bestPath.size() == n) goto OUTPUT;
    }

    // Randomized attempts
    {
        int randomTries = 12;
        for (int t = 0; t < randomTries; t++) {
            fisherYatesShuffle(ordRand, rng);
            auto p = runAttempt(ordRand);
            if (p.size() > bestPath.size()) bestPath = std::move(p);
            if ((int)bestPath.size() == n) break;
        }
    }

OUTPUT:
    fw.writeInt((int)bestPath.size(), '\n');
    for (size_t i = 0; i < bestPath.size(); i++) {
        fw.writeInt(bestPath[i], i + 1 == bestPath.size() ? '\n' : ' ');
    }
    fw.flush();
    return 0;
}