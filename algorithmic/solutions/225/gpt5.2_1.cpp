#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr int SZ = 1 << 20;
    int idx = 0, size = 0;
    char buf[SZ];

    inline char readChar() {
        if (idx >= size) {
            size = (int)fread(buf, 1, SZ, stdin);
            idx = 0;
            if (size == 0) return 0;
        }
        return buf[idx++];
    }

    int nextInt() {
        char c;
        do c = readChar();
        while (c <= ' ' && c);
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

struct FastWriter {
    static constexpr size_t SZ = 1 << 20;
    size_t idx = 0;
    char buf[SZ];

    ~FastWriter() { flush(); }

    inline void flush() {
        if (idx) {
            fwrite(buf, 1, idx, stdout);
            idx = 0;
        }
    }

    inline void writeChar(char c) {
        if (idx == SZ) flush();
        buf[idx++] = c;
    }

    inline void writeInt(int x) {
        if (x == 0) { writeChar('0'); return; }
        if (x < 0) { writeChar('-'); x = -x; }
        char s[24];
        int n = 0;
        while (x) { s[n++] = char('0' + (x % 10)); x /= 10; }
        while (n--) writeChar(s[n]);
    }
};

struct Node {
    int L = 0, R = 0;
    int left = -1, right = -1;
    vector<int> pos;      // sorted permutation indices of values in [L,R]
    vector<int> prefL;    // prefix count of elements from left child in merged pos (size pos.size()+1)
    vector<int> seg;      // triangular storage of set IDs for all segments [l..r] in pos
};

static inline int triIndex(int m, int l, int r) {
    return l * m - (l * (l - 1)) / 2 + (r - l);
}

static inline int lowerBoundVec(const vector<int>& v, int x) {
    int l = 0, r = (int)v.size();
    while (l < r) {
        int mid = (l + r) >> 1;
        if (v[mid] < x) l = mid + 1;
        else r = mid;
    }
    return l;
}

static inline int upperBoundVec(const vector<int>& v, int x) {
    int l = 0, r = (int)v.size();
    while (l < r) {
        int mid = (l + r) >> 1;
        if (v[mid] <= x) l = mid + 1;
        else r = mid;
    }
    return l;
}

struct Builder {
    int n = 0;
    int cnt = 0;
    vector<int> a;            // 1-indexed
    vector<int> posOfVal;     // 1-indexed: value -> permutation index (also singleton set id)
    vector<Node> nodes;
    vector<pair<int,int>> ops;
    vector<int> mn, mx;       // min/max value in set id

    Builder(int n_, vector<int> a_, vector<int> pos_) : n(n_), cnt(n_), a(std::move(a_)), posOfVal(std::move(pos_)) {
        nodes.reserve(2 * n + 64);
        ops.reserve(2200000);
        mn.reserve(2200005);
        mx.reserve(2200005);
        mn.resize(n + 1);
        mx.resize(n + 1);
        mn[0] = INT_MAX;
        mx[0] = INT_MIN;
        for (int i = 1; i <= n; i++) {
            mn[i] = mx[i] = a[i];
        }
    }

    inline int mergeSets(int u, int v) {
        // assumes mx[u] < mn[v]
        ++cnt;
        ops.emplace_back(u, v);
        mn.push_back(mn[u]);
        mx.push_back(mx[v]);
        return cnt;
    }

    inline int getSeg(int nodeIdx, int l, int r) const {
        if (l > r) return 0;
        const Node &nd = nodes[nodeIdx];
        int m = (int)nd.pos.size();
        return nd.seg[triIndex(m, l, r)];
    }

    int buildNode(int L, int R) {
        int idx = (int)nodes.size();
        nodes.emplace_back();
        Node &nd = nodes[idx];
        nd.L = L; nd.R = R;

        if (L == R) {
            nd.pos = { posOfVal[L] };
            nd.seg = { posOfVal[L] };
            return idx;
        }

        int mid = (L + R) >> 1;
        nd.left = buildNode(L, mid);
        nd.right = buildNode(mid + 1, R);

        const vector<int> &lp = nodes[nd.left].pos;
        const vector<int> &rp = nodes[nd.right].pos;

        nd.pos.reserve(lp.size() + rp.size());
        nd.prefL.resize(lp.size() + rp.size() + 1);
        nd.prefL[0] = 0;

        size_t i = 0, j = 0, k = 0;
        while (i < lp.size() || j < rp.size()) {
            if (j == rp.size() || (i < lp.size() && lp[i] < rp[j])) {
                nd.pos.push_back(lp[i++]);
                nd.prefL[k + 1] = nd.prefL[k] + 1;
            } else {
                nd.pos.push_back(rp[j++]);
                nd.prefL[k + 1] = nd.prefL[k];
            }
            ++k;
        }

        int m = (int)nd.pos.size();
        nd.seg.resize(m * (m + 1) / 2);

        for (int l = 0; l < m; l++) {
            int prefL_l = nd.prefL[l];
            int rightStartBase = l - prefL_l;
            for (int r = l; r < m; r++) {
                int prefL_r1 = nd.prefL[r + 1];

                int ls = prefL_l;
                int le = prefL_r1;
                int rs = rightStartBase;
                int re = (r + 1) - prefL_r1;

                int leftId = (ls < le) ? getSeg(nd.left, ls, le - 1) : 0;
                int rightId = (rs < re) ? getSeg(nd.right, rs, re - 1) : 0;

                int id;
                if (leftId == 0) id = rightId;
                else if (rightId == 0) id = leftId;
                else {
                    // left child values are < right child values by construction
                    id = mergeSets(leftId, rightId);
                }

                nd.seg[triIndex(m, l, r)] = id;
            }
        }

        return idx;
    }

    inline int bucketPiece(int bucketRoot, int lIdx, int rIdx) const {
        const Node &root = nodes[bucketRoot];
        const vector<int> &v = root.pos;
        int i = lowerBoundVec(v, lIdx);
        int j = upperBoundVec(v, rIdx) - 1;
        if (i > j) return 0;
        return getSeg(bucketRoot, i, j);
    }
};

int main() {
    FastScanner fs;
    int n = fs.nextInt();
    int q = fs.nextInt();
    vector<int> a(n + 1), posOfVal(n + 1);
    for (int i = 1; i <= n; i++) {
        a[i] = fs.nextInt();
        posOfVal[a[i]] = i;
    }

    Builder builder(n, a, posOfVal);

    int B = min(16, n);
    vector<int> bucketRoots;
    bucketRoots.reserve(B);

    for (int b = 0; b < B; b++) {
        int L = (int)((1LL * b * n) / B) + 1;
        int R = (int)((1LL * (b + 1) * n) / B);
        if (L <= R) {
            int root = builder.buildNode(L, R);
            bucketRoots.push_back(root);
        }
    }

    vector<int> ans(q);
    for (int i = 0; i < q; i++) {
        int l = fs.nextInt();
        int r = fs.nextInt();
        int cur = 0;
        for (int root : bucketRoots) {
            int piece = builder.bucketPiece(root, l, r);
            if (!piece) continue;
            if (!cur) cur = piece;
            else cur = builder.mergeSets(cur, piece);
        }
        ans[i] = cur;
    }

    if (builder.cnt > 2200000) {
        // Should not happen with chosen parameters; still output something valid if it does.
        // (Problem guarantees existence; this fallback is just a guard.)
        // We'll output current construction anyway.
    }

    FastWriter fw;
    fw.writeInt(builder.cnt);
    fw.writeChar('\n');
    for (auto &op : builder.ops) {
        fw.writeInt(op.first);
        fw.writeChar(' ');
        fw.writeInt(op.second);
        fw.writeChar('\n');
    }
    for (int i = 0; i < q; i++) {
        if (i) fw.writeChar(' ');
        fw.writeInt(ans[i]);
    }
    fw.writeChar('\n');
    fw.flush();
    return 0;
}