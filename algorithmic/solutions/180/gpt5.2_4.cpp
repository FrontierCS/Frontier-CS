#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr size_t BUFSIZE = 1 << 20;
    unsigned char buf[BUFSIZE];
    size_t idx = 0, size = 0;

    inline unsigned char readByte() {
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
            c = readByte();
            if (!c) return false;
        } while (c <= ' ');

        bool neg = false;
        if (c == '-') {
            neg = true;
            c = readByte();
        }

        T val = 0;
        while (c > ' ') {
            val = val * 10 + (c - '0');
            c = readByte();
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

static inline uint64_t rotl64(uint64_t x, int r) {
    return (x << r) | (x >> (64 - r));
}

struct SigItem {
    uint64_t a, b;
    int g;   // 0 or 1
    int v;   // vertex index
    bool operator<(const SigItem& other) const {
        if (a != other.a) return a < other.a;
        if (b != other.b) return b < other.b;
        if (g != other.g) return g < other.g;
        return v < other.v;
    }
};

struct Key {
    int col;
    int deg;
    uint64_t sum;
    uint64_t xr;
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int n;
    int m;
    if (!fs.readInt(n)) return 0;
    fs.readInt(m);

    vector<vector<int>> adj1(n), adj2(n);
    adj1.assign(n, {});
    adj2.assign(n, {});
    adj1.reserve(n);
    adj2.reserve(n);

    adj1.shrink_to_fit(); // keep vector overhead reasonable (no-op mostly)

    // Read edges of G1
    for (int i = 0; i < m; i++) {
        int u, v;
        fs.readInt(u); fs.readInt(v);
        --u; --v;
        adj1[u].push_back(v);
        adj1[v].push_back(u);
    }
    // Read edges of G2
    for (int i = 0; i < m; i++) {
        int u, v;
        fs.readInt(u); fs.readInt(v);
        --u; --v;
        adj2[u].push_back(v);
        adj2[v].push_back(u);
    }

    vector<int> deg1(n), deg2(n);
    for (int i = 0; i < n; i++) {
        deg1[i] = (int)adj1[i].size();
        deg2[i] = (int)adj2[i].size();
    }

    vector<int> col1(n), col2(n), newcol1(n), newcol2(n);
    for (int i = 0; i < n; i++) {
        col1[i] = deg1[i];
        col2[i] = deg2[i];
    }

    const int ITERS = 8;
    const uint64_t SEED_A1 = 0x123456789abcdef0ULL;
    const uint64_t SEED_A2 = 0x0fedcba987654321ULL;
    const uint64_t SEED_B1 = 0x9e3779b97f4a7c15ULL;
    const uint64_t SEED_B2 = 0xbf58476d1ce4e5b9ULL;
    const uint64_t SEED_C1 = 0x94d049bb133111ebULL;
    const uint64_t SEED_C2 = 0x2545F4914F6CDD1DULL;

    vector<SigItem> items;
    items.reserve(2 * (size_t)n);

    for (int iter = 0; iter < ITERS; iter++) {
        items.clear();

        auto addGraphItems = [&](int g, const vector<vector<int>>& adj, const vector<int>& col, const vector<int>& deg) {
            for (int v = 0; v < n; v++) {
                uint64_t s1 = 0, s2 = 0, s3 = 0, s4 = 0;
                for (int u : adj[v]) {
                    uint64_t x1 = splitmix64((uint64_t)col[u] + SEED_A1);
                    uint64_t x2 = splitmix64((uint64_t)col[u] + SEED_A2);
                    s1 += x1;
                    s2 ^= x1 * SEED_B1;
                    s3 += x2;
                    s4 ^= x2 * SEED_B2;
                }

                uint64_t h1 = splitmix64(s1 ^ (s2 + SEED_C1) ^ (uint64_t)col[v] * 0xD6E8FEB86659FD93ULL);
                h1 = splitmix64(h1 ^ ((uint64_t)deg[v] * 0xA24BAED4963EE407ULL) ^ (uint64_t)adj[v].size());

                uint64_t h2 = splitmix64(s3 ^ (s4 + SEED_C2) ^ (uint64_t)col[v] * 0x9FB21C651E98DF25ULL);
                h2 = splitmix64(h2 ^ ((uint64_t)deg[v] * 0xC3A5C85C97CB3127ULL) ^ ((uint64_t)adj[v].size() << 1));

                items.push_back({h1, h2, g, v});
            }
        };

        addGraphItems(0, adj1, col1, deg1);
        addGraphItems(1, adj2, col2, deg2);

        sort(items.begin(), items.end());

        int curColor = -1;
        uint64_t lastA = 0, lastB = 0;
        bool first = true;

        for (auto &it : items) {
            if (first || it.a != lastA || it.b != lastB) {
                curColor++;
                lastA = it.a;
                lastB = it.b;
                first = false;
            }
            if (it.g == 0) newcol1[it.v] = curColor;
            else newcol2[it.v] = curColor;
        }

        col1.swap(newcol1);
        col2.swap(newcol2);
    }

    vector<Key> key1(n), key2(n);
    const uint64_t KEYSEED = 0x7f4a7c159e3779b9ULL;

    auto computeKeys = [&](const vector<vector<int>>& adj, const vector<int>& col, const vector<int>& deg, vector<Key>& key) {
        for (int v = 0; v < n; v++) {
            uint64_t sum = 0, xr = 0;
            for (int u : adj[v]) {
                uint64_t cu = (uint64_t)col[u] + 1;
                sum += cu;
                uint64_t h = splitmix64(cu + KEYSEED);
                xr ^= rotl64(h, (int)(h & 63));
            }
            key[v] = Key{col[v], deg[v], sum, xr};
        }
    };

    computeKeys(adj1, col1, deg1, key1);
    computeKeys(adj2, col2, deg2, key2);

    vector<int> idx1(n), idx2(n);
    iota(idx1.begin(), idx1.end(), 0);
    iota(idx2.begin(), idx2.end(), 0);

    auto cmpIdx = [&](const vector<Key>& key, int a, int b) {
        const Key &ka = key[a], &kb = key[b];
        if (ka.col != kb.col) return ka.col < kb.col;
        if (ka.deg != kb.deg) return ka.deg < kb.deg;
        if (ka.sum != kb.sum) return ka.sum < kb.sum;
        if (ka.xr != kb.xr) return ka.xr < kb.xr;
        return a < b;
    };

    sort(idx1.begin(), idx1.end(), [&](int a, int b){ return cmpIdx(key1, a, b); });
    sort(idx2.begin(), idx2.end(), [&](int a, int b){ return cmpIdx(key2, a, b); });

    vector<int> map2to1(n, -1);
    for (int i = 0; i < n; i++) {
        map2to1[idx2[i]] = idx1[i];
    }

    for (int i = 0; i < n; i++) {
        if (i) cout << ' ';
        cout << (map2to1[i] + 1);
    }
    cout << '\n';
    return 0;
}