#include <bits/stdc++.h>
using namespace std;

static const int MAXV = 1 << 12; // 4096
static const int BASE = 16;
static const int LEVELS = 5; // 16,32,64,128,256

struct FastScanner {
    static const int BUFSIZE = 1 << 20;
    int idx, size;
    char buf[BUFSIZE];
    FastScanner() : idx(0), size(0) {}
    inline char read() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSIZE, stdin);
            idx = 0;
            if (!size) return 0;
        }
        return buf[idx++];
    }
    template <class T>
    bool readInt(T &out) {
        char c;
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

struct FastOutput {
    static const int BUFSIZE = 1 << 20;
    int idx;
    char buf[BUFSIZE];
    FastOutput() : idx(0) {}
    ~FastOutput() { flush(); }
    inline void flush() {
        if (idx) {
            fwrite(buf, 1, idx, stdout);
            idx = 0;
        }
    }
    inline void pc(char c) {
        if (idx >= BUFSIZE) flush();
        buf[idx++] = c;
    }
    inline void writeInt(int x) {
        if (x == 0) { pc('0'); return; }
        if (x < 0) { pc('-'); x = -x; }
        char s[16];
        int n = 0;
        while (x) { s[n++] = char('0' + (x % 10)); x /= 10; }
        while (n--) pc(s[n]);
    }
    inline void writeSpace() { pc(' '); }
    inline void writeLn() { pc('\n'); }
};

struct Op { int u, v; };

struct Bucket {
    vector<int> pos; // sorted positions of values in this value interval
    vector<int> tab; // triangular matrix of set IDs for blocks in pos-order
};

static inline int triIndex(int i, int j, int m) {
    // i <= j, 0-based, row i has (m-i) entries
    // offset(i) = i*m - i*(i-1)/2
    return i * m - (i * (i - 1)) / 2 + (j - i);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int n, q;
    if (!fs.readInt(n)) return 0;
    fs.readInt(q);

    vector<int> a(n + 1);
    vector<int> posOfVal(n + 1, 0);
    for (int i = 1; i <= n; i++) {
        fs.readInt(a[i]);
        posOfVal[a[i]] = i;
    }

    vector<Op> ops;
    ops.reserve(2200000);

    int cnt = n;

    auto mergeSets = [&](int u, int v) -> int {
        // u and v must exist, and max(u)<min(v) guaranteed by construction
        ops.push_back({u, v});
        return ++cnt;
    };

    // levels[0] => 256 buckets of size 16 values each; levels[4] => 16 buckets of size 256
    vector<vector<Bucket>> levels(LEVELS);
    for (int lv = 0; lv < LEVELS; lv++) levels[lv].resize((MAXV / BASE) >> lv);

    // Build level 0 buckets (size 16) with insertion via a value segment tree of size 16.
    for (int b = 0; b < (int)levels[0].size(); b++) {
        int startVal = b * BASE + 1;
        Bucket &bk = levels[0][b];

        vector<int> pos;
        pos.reserve(BASE);
        for (int v = startVal; v < startVal + BASE && v <= n; v++) {
            pos.push_back(posOfVal[v]);
        }
        sort(pos.begin(), pos.end());
        bk.pos = std::move(pos);

        int m = (int)bk.pos.size();
        bk.tab.assign(m * (m + 1) / 2, 0);
        if (m == 0) continue;

        struct VNode { int lch, rch, setId; };
        vector<VNode> pool;
        pool.reserve(1 + m * (m + 1) / 2 * 5);
        pool.push_back({0, 0, 0}); // node 0 = empty

        auto newNode = [&](int lch, int rch, int setId) -> int {
            pool.push_back({lch, rch, setId});
            return (int)pool.size() - 1;
        };

        function<int(int,int,int,int,int)> upd = [&](int node, int l, int r, int posIdx, int leafSetId) -> int {
            if (l == r) {
                return newNode(0, 0, leafSetId);
            }
            int mid = (l + r) >> 1;
            int lch = pool[node].lch;
            int rch = pool[node].rch;
            int nlch = lch, nrch = rch;
            if (posIdx <= mid) nlch = upd(lch, l, mid, posIdx, leafSetId);
            else nrch = upd(rch, mid + 1, r, posIdx, leafSetId);

            int leftSet = pool[nlch].setId;
            int rightSet = pool[nrch].setId;
            int setId;
            if (leftSet == 0) setId = rightSet;
            else if (rightSet == 0) setId = leftSet;
            else setId = mergeSets(leftSet, rightSet);

            return newNode(nlch, nrch, setId);
        };

        for (int i = 0; i < m; i++) {
            int root = 0;
            for (int j = i; j < m; j++) {
                int p = bk.pos[j];
                int v = a[p];
                int leafIdx = v - startVal; // 0..15
                root = upd(root, 0, BASE - 1, leafIdx, p);
                bk.tab[triIndex(i, j, m)] = pool[root].setId;
            }
        }
    }

    auto getSet = [&](const Bucket &bk, int l, int r) -> int {
        const auto &pos = bk.pos;
        int m = (int)pos.size();
        if (m == 0) return 0;
        int i = (int)(lower_bound(pos.begin(), pos.end(), l) - pos.begin());
        int j = (int)(upper_bound(pos.begin(), pos.end(), r) - pos.begin()) - 1;
        if (i > j) return 0;
        return bk.tab[triIndex(i, j, m)];
    };

    // Build higher levels up to size 256 buckets.
    for (int lv = 1; lv < LEVELS; lv++) {
        int cntBuckets = (int)levels[lv].size();
        for (int bi = 0; bi < cntBuckets; bi++) {
            const Bucket &L = levels[lv - 1][2 * bi];
            const Bucket &R = levels[lv - 1][2 * bi + 1];
            Bucket &P = levels[lv][bi];

            P.pos.clear();
            P.pos.reserve(L.pos.size() + R.pos.size());
            merge(L.pos.begin(), L.pos.end(), R.pos.begin(), R.pos.end(), back_inserter(P.pos));

            int m = (int)P.pos.size();
            P.tab.assign(m * (m + 1) / 2, 0);
            if (m == 0) continue;

            for (int i = 0; i < m; i++) {
                int l = P.pos[i];
                for (int j = i; j < m; j++) {
                    int r = P.pos[j];
                    int leftId = getSet(L, l, r);
                    int rightId = getSet(R, l, r);
                    int setId;
                    if (leftId == 0) setId = rightId;
                    else if (rightId == 0) setId = leftId;
                    else setId = mergeSets(leftId, rightId);
                    P.tab[triIndex(i, j, m)] = setId;
                }
            }
        }
    }

    // Answer queries by merging across level-4 buckets (size 256).
    vector<int> ans(q);
    for (int qi = 0; qi < q; qi++) {
        int l, r;
        fs.readInt(l);
        fs.readInt(r);

        int cur = 0;
        for (int b = 0; b < (int)levels[4].size(); b++) {
            int id = getSet(levels[4][b], l, r);
            if (id == 0) continue;
            if (cur == 0) cur = id;
            else cur = mergeSets(cur, id);
        }
        ans[qi] = cur;
    }

    // Output
    FastOutput fo;
    fo.writeInt(cnt);
    fo.writeLn();
    for (const auto &op : ops) {
        fo.writeInt(op.u);
        fo.writeSpace();
        fo.writeInt(op.v);
        fo.writeLn();
    }
    for (int i = 0; i < q; i++) {
        if (i) fo.writeSpace();
        fo.writeInt(ans[i]);
    }
    fo.writeLn();
    fo.flush();
    return 0;
}