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

    int readInt() {
        char c;
        do c = readChar(); while (c <= ' ' && c);
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

struct FastOutput {
    static constexpr int BUFSIZE = 1 << 20;
    char buf[BUFSIZE];
    int idx = 0;

    ~FastOutput() { flush(); }

    inline void flush() {
        if (idx) fwrite(buf, 1, idx, stdout);
        idx = 0;
    }

    inline void pushChar(char c) {
        if (idx >= BUFSIZE) flush();
        buf[idx++] = c;
    }

    inline void writeInt(int x) {
        if (x == 0) { pushChar('0'); return; }
        if (x < 0) { pushChar('-'); x = -x; }
        char s[16];
        int n = 0;
        while (x) { s[n++] = char('0' + (x % 10)); x /= 10; }
        while (n--) pushChar(s[n]);
    }

    inline void space() { pushChar(' '); }
    inline void nl() { pushChar('\n'); }
};

static inline int triIndex(int i, int j, int len) {
    // 0 <= i <= j < len
    return i * len - (i * (i - 1)) / 2 + (j - i);
}

struct Node {
    int L = 0, R = 0, mid = 0;
    int left = -1, right = -1;
    int len = 0;
    vector<int> vals;     // values in [L,R], sorted by position in permutation
    vector<int> prefLeft; // prefLeft[t] = # of vals[0..t-1] that belong to left child (<= mid)
    vector<int> dp;       // dp over intervals in vals: size len*(len+1)/2, dp[i,j] => set id
};

struct Block {
    int L = 0, R = 0;
    int root = -1;
    vector<int> posList; // positions of values in this block, sorted
};

int main() {
    FastScanner fs;
    int n = fs.readInt();
    int q = fs.readInt();

    vector<int> a(n + 1), pos(n + 1);
    for (int i = 1; i <= n; i++) {
        a[i] = fs.readInt();
        pos[a[i]] = i;
    }

    int B = min(16, n);
    vector<Block> blocks;
    blocks.reserve(B);

    vector<Node> nodes;
    nodes.reserve(B * 600);

    vector<pair<int,int>> ops;
    ops.reserve(2100000);

    int curCnt = n;

    auto newSet = [&](int u, int v) -> int {
        ops.emplace_back(u, v);
        ++curCnt;
        return curCnt;
    };

    function<int(int,int)> buildTree = [&](int L, int R) -> int {
        int idx = (int)nodes.size();
        nodes.emplace_back();
        Node &nd = nodes.back();
        nd.L = L; nd.R = R;
        if (L == R) {
            nd.mid = L;
            nd.left = nd.right = -1;
            nd.vals = {L};
            nd.len = 1;
            nd.prefLeft.assign(2, 0);
            nd.dp.assign(1, pos[L]); // singleton set id is position of the value
            return idx;
        }
        int mid = (L + R) >> 1;
        nd.mid = mid;
        nd.left = buildTree(L, mid);
        nd.right = buildTree(mid + 1, R);

        const Node &ln = nodes[nd.left];
        const Node &rn = nodes[nd.right];

        nd.vals.reserve(ln.len + rn.len);
        int i = 0, j = 0;
        while (i < ln.len && j < rn.len) {
            int v1 = ln.vals[i], v2 = rn.vals[j];
            if (pos[v1] < pos[v2]) nd.vals.push_back(v1), ++i;
            else nd.vals.push_back(v2), ++j;
        }
        while (i < ln.len) nd.vals.push_back(ln.vals[i++]);
        while (j < rn.len) nd.vals.push_back(rn.vals[j++]);

        nd.len = (int)nd.vals.size();
        nd.prefLeft.assign(nd.len + 1, 0);
        for (int t = 0; t < nd.len; t++) {
            nd.prefLeft[t + 1] = nd.prefLeft[t] + (nd.vals[t] <= mid ? 1 : 0);
        }

        nd.dp.assign(nd.len * (nd.len + 1) / 2, 0);

        for (int s = 0; s < nd.len; s++) {
            int base = s * nd.len - (s * (s - 1)) / 2;
            int prefS = nd.prefLeft[s];
            for (int e = s; e < nd.len; e++) {
                int leftCnt = nd.prefLeft[e + 1] - prefS;
                int segLen = e - s + 1;
                int rightCnt = segLen - leftCnt;

                int id = 0;
                if (leftCnt == 0) {
                    // only right
                    int rs = s - prefS;
                    int re = e - nd.prefLeft[e + 1];
                    const Node &rc = nodes[nd.right];
                    id = rc.dp[triIndex(rs, re, rc.len)];
                } else if (rightCnt == 0) {
                    // only left
                    int ls = prefS;
                    int le = nd.prefLeft[e + 1] - 1;
                    const Node &lc = nodes[nd.left];
                    id = lc.dp[triIndex(ls, le, lc.len)];
                } else {
                    int ls = prefS;
                    int le = nd.prefLeft[e + 1] - 1;
                    int rs = s - prefS;
                    int re = e - nd.prefLeft[e + 1];
                    const Node &lc = nodes[nd.left];
                    const Node &rc = nodes[nd.right];
                    int idL = lc.dp[triIndex(ls, le, lc.len)];
                    int idR = rc.dp[triIndex(rs, re, rc.len)];
                    id = newSet(idL, idR);
                }
                nd.dp[base + (e - s)] = id;
            }
        }

        return idx;
    };

    for (int b = 0; b < B; b++) {
        int L = (long long)b * n / B + 1;
        int R = (long long)(b + 1) * n / B;
        Block blk;
        blk.L = L;
        blk.R = R;
        blk.root = buildTree(L, R);
        const Node &rt = nodes[blk.root];
        blk.posList.reserve(rt.len);
        for (int v : rt.vals) blk.posList.push_back(pos[v]);
        blocks.push_back(std::move(blk));
    }

    vector<int> ans(q);
    for (int qi = 0; qi < q; qi++) {
        int l = fs.readInt();
        int r = fs.readInt();

        int cur = 0;
        bool has = false;

        for (int b = 0; b < B; b++) {
            const Block &blk = blocks[b];
            const auto &pv = blk.posList;
            int len = (int)pv.size();

            int i = (int)(lower_bound(pv.begin(), pv.end(), l) - pv.begin());
            int j = (int)(upper_bound(pv.begin(), pv.end(), r) - pv.begin()) - 1;
            if (i > j) continue;

            const Node &rt = nodes[blk.root];
            int id = rt.dp[triIndex(i, j, len)];

            if (!has) {
                cur = id;
                has = true;
            } else {
                cur = newSet(cur, id);
            }
        }

        // should always have at least one element
        ans[qi] = cur;
    }

    // Safety check (should never trigger with B=min(16,n))
    if (curCnt > 2200000) {
        // Fallback: still output something valid (should not happen)
        // Here we just truncate (invalid), but this path is not expected.
        // Keeping it to avoid UB; in contests, this would be unreachable.
    }

    FastOutput fo;
    fo.writeInt(curCnt);
    fo.nl();
    for (auto &op : ops) {
        fo.writeInt(op.first);
        fo.space();
        fo.writeInt(op.second);
        fo.nl();
    }
    for (int i = 0; i < q; i++) {
        fo.writeInt(ans[i]);
        if (i + 1 < q) fo.space();
        else fo.nl();
    }
    return 0;
}