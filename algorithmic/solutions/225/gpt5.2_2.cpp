#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr size_t BUFSIZE = 1 << 20;
    int idx = 0, size = 0;
    char buf[BUFSIZE];

    inline char readChar() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }

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

struct FastOutput {
    static constexpr size_t BUFSIZE = 1 << 20;
    size_t idx = 0;
    char buf[BUFSIZE];

    ~FastOutput() { flush(); }

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

    inline void writeUInt(uint32_t x) {
        char s[16];
        int n = 0;
        while (x) {
            s[n++] = char('0' + (x % 10));
            x /= 10;
        }
        if (!n) s[n++] = '0';
        while (n--) pushChar(s[n]);
    }

    inline void writeInt(int x) {
        if (x < 0) {
            pushChar('-');
            writeUInt((uint32_t)(-x));
        } else {
            writeUInt((uint32_t)x);
        }
    }

    inline void writeSpace() { pushChar(' '); }
    inline void writeNewline() { pushChar('\n'); }
};

static inline uint64_t splitmix64(uint64_t x) {
    x += 0x9e3779b97f4a7c15ULL;
    x = (x ^ (x >> 30)) * 0xbf58476d1ce4e5b9ULL;
    x = (x ^ (x >> 27)) * 0x94d049bb133111ebULL;
    return x ^ (x >> 31);
}

struct HashMap {
    int mask;
    vector<uint64_t> keys;
    vector<int> vals;
    int sz = 0;

    explicit HashMap(int capacityPow2) {
        int cap = 1;
        while (cap < capacityPow2) cap <<= 1;
        keys.assign(cap, 0);
        vals.assign(cap, 0);
        mask = cap - 1;
    }

    inline bool get(uint64_t key, int &out) const {
        uint64_t h = splitmix64(key);
        int i = (int)(h & (uint64_t)mask);
        while (true) {
            uint64_t k = keys[i];
            if (k == 0) return false;
            if (k == key) {
                out = vals[i];
                return true;
            }
            i = (i + 1) & mask;
        }
    }

    inline void set(uint64_t key, int val) {
        uint64_t h = splitmix64(key);
        int i = (int)(h & (uint64_t)mask);
        while (true) {
            uint64_t k = keys[i];
            if (k == 0) {
                keys[i] = key;
                vals[i] = val;
                ++sz;
                return;
            }
            if (k == key) {
                vals[i] = val;
                return;
            }
            i = (i + 1) & mask;
        }
    }
};

struct Node {
    int L, R, mid;
    int left = -1, right = -1;
    int len = 0;
    int leafId = 0;
    vector<int> pref; // size len+1, pref[i]=count of elements <= mid in first i positions (1-indexed positions)

    inline bool isLeaf() const { return L == R; }
};

static const int LR_BITS = 13; // enough for indices up to 4096 (including 4096)
static inline uint64_t packKey(int nodeId, int l, int r) {
    return ( (uint64_t)nodeId << (2 * LR_BITS) ) | ( (uint64_t)l << LR_BITS ) | (uint64_t)r;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int n, q;
    if (!fs.readInt(n)) return 0;
    fs.readInt(q);

    vector<int> a(n + 1), pos(n + 1);
    for (int i = 1; i <= n; i++) {
        fs.readInt(a[i]);
        pos[a[i]] = i;
    }

    vector<Node> nodes;
    nodes.reserve(2 * n + 5);

    function<int(int,int, const vector<int>&)> build = [&](int L, int R, const vector<int>& seq) -> int {
        int id = (int)nodes.size();
        nodes.push_back(Node());
        Node &nd = nodes.back();
        nd.L = L; nd.R = R;
        nd.len = (int)seq.size();
        if (L == R) {
            nd.leafId = pos[L];
            return id;
        }
        nd.mid = (L + R) >> 1;
        nd.pref.assign(nd.len + 1, 0);
        vector<int> leftSeq;
        vector<int> rightSeq;
        leftSeq.reserve(nd.len / 2 + 2);
        rightSeq.reserve(nd.len / 2 + 2);
        for (int i = 0; i < nd.len; i++) {
            int v = seq[i];
            nd.pref[i + 1] = nd.pref[i] + (v <= nd.mid);
            if (v <= nd.mid) leftSeq.push_back(v);
            else rightSeq.push_back(v);
        }
        nd.left = build(L, nd.mid, leftSeq);
        nd.right = build(nd.mid + 1, R, rightSeq);
        return id;
    };

    vector<int> rootSeq;
    rootSeq.reserve(n);
    for (int i = 1; i <= n; i++) rootSeq.push_back(a[i]);
    int root = build(1, n, rootSeq);

    int cnt = n;
    vector<pair<int,int>> ops;
    ops.reserve(2100000);

    // Maximum memo entries is safely below ~2.1e6, allocate ~4.2e6 slots.
    HashMap memo(1 << 22);

    auto doMerge = [&](int u, int v) -> int {
        ops.push_back({u, v});
        return ++cnt;
    };

    function<int(int,int,int)> getSet = [&](int nodeId, int l, int r) -> int {
        if (l > r) return 0;
        const Node &nd = nodes[nodeId];
        if (nd.isLeaf()) return nd.leafId;

        uint64_t key = packKey(nodeId, l, r);
        int cached;
        if (memo.get(key, cached)) return cached;

        int leftL = nd.pref[l - 1] + 1;
        int leftR = nd.pref[r];
        int rightL = (l - 1 - nd.pref[l - 1]) + 1;
        int rightR = (r - nd.pref[r]);

        int leftId = (leftL <= leftR) ? getSet(nd.left, leftL, leftR) : 0;
        int rightId = (rightL <= rightR) ? getSet(nd.right, rightL, rightR) : 0;

        int res;
        if (!leftId) res = rightId;
        else if (!rightId) res = leftId;
        else res = doMerge(leftId, rightId);

        memo.set(key, res);
        return res;
    };

    vector<int> ans(q);
    for (int i = 0; i < q; i++) {
        int l, r;
        fs.readInt(l);
        fs.readInt(r);
        ans[i] = getSet(root, l, r);
    }

    FastOutput fo;
    fo.writeInt(cnt);
    fo.writeNewline();
    for (auto [u, v] : ops) {
        fo.writeInt(u);
        fo.writeSpace();
        fo.writeInt(v);
        fo.writeNewline();
    }
    for (int i = 0; i < q; i++) {
        if (i) fo.writeSpace();
        fo.writeInt(ans[i]);
    }
    fo.writeNewline();
    fo.flush();
    return 0;
}