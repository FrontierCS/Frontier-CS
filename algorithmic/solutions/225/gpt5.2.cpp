#include <bits/stdc++.h>
using namespace std;

struct FastScanner {
    static constexpr size_t BUFSZ = 1 << 20;
    int idx = 0, size = 0;
    char buf[BUFSZ];

    inline char readChar() {
        if (idx >= size) {
            size = (int)fread(buf, 1, BUFSZ, stdin);
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
    static constexpr size_t BUFSZ = 1 << 20;
    size_t idx = 0;
    char buf[BUFSZ];

    ~FastOutput() { flush(); }

    inline void flush() {
        if (idx) {
            fwrite(buf, 1, idx, stdout);
            idx = 0;
        }
    }

    inline void writeChar(char c) {
        if (idx >= BUFSZ) flush();
        buf[idx++] = c;
    }

    inline void writeInt(int x) {
        if (x == 0) {
            writeChar('0');
            return;
        }
        if (x < 0) {
            writeChar('-');
            x = -x;
        }
        char s[16];
        int n = 0;
        while (x) {
            s[n++] = char('0' + (x % 10));
            x /= 10;
        }
        while (n--) writeChar(s[n]);
    }

    inline void writeStr(const char* s) {
        while (*s) writeChar(*s++);
    }
};

static const int CNT_LIMIT = 2200000;

static int g_cnt;
static vector<pair<int,int>> g_ops;

static inline int newSet(int u, int v) {
    // assumes validity of merge condition is ensured by construction
    ++g_cnt;
    g_ops.emplace_back(u, v);
    return g_cnt;
}

struct Node {
    int s = 0;
    vector<int> vals;    // values in increasing position order (pos[value])
    vector<int> seg;     // set id for each segment [l,r] in vals
    vector<int> offset;  // offset[l] -> start index in seg for segments starting at l (1-indexed)

    inline int get(int l, int r) const {
        // 1 <= l <= r <= s
        return seg[offset[l] + (r - l)];
    }
};

static Node buildRange(int L, int R, const vector<int> &posOfValue, const vector<int> &idValue) {
    if (L == R) {
        Node node;
        node.s = 1;
        node.vals = {L};
        node.offset.assign(3, 0);
        node.offset[1] = 0;
        node.offset[2] = 1;
        node.seg = {idValue[L]};
        return node;
    }

    int mid = (L + R) >> 1;
    Node left = buildRange(L, mid, posOfValue, idValue);
    Node right = buildRange(mid + 1, R, posOfValue, idValue);

    Node node;
    node.s = left.s + right.s;
    node.vals.reserve(node.s);

    vector<unsigned char> side;
    side.reserve(node.s);

    int i = 0, j = 0;
    while (i < left.s && j < right.s) {
        int vl = left.vals[i];
        int vr = right.vals[j];
        if (posOfValue[vl] < posOfValue[vr]) {
            node.vals.push_back(vl);
            side.push_back(0);
            ++i;
        } else {
            node.vals.push_back(vr);
            side.push_back(1);
            ++j;
        }
    }
    while (i < left.s) {
        node.vals.push_back(left.vals[i++]);
        side.push_back(0);
    }
    while (j < right.s) {
        node.vals.push_back(right.vals[j++]);
        side.push_back(1);
    }

    int s = node.s;

    node.offset.assign(s + 2, 0);
    node.offset[1] = 0;
    for (int l = 2; l <= s + 1; ++l) {
        node.offset[l] = node.offset[l - 1] + (s - l + 2);
    }
    int totSeg = node.offset[s + 1];
    node.seg.assign(totSeg, 0);

    vector<int> preL(s + 1, 0);
    for (int t = 1; t <= s; ++t) preL[t] = preL[t - 1] + (side[t - 1] == 0);

    for (int l = 1; l <= s; ++l) {
        int base = node.offset[l];
        int leftBefore = preL[l - 1];
        int rightBefore = (l - 1) - leftBefore;

        for (int r = l; r <= s; ++r) {
            int leftCount = preL[r] - leftBefore;
            int len = r - l + 1;
            int rightCount = len - leftCount;

            int leftID = 0, rightID = 0;
            if (leftCount > 0) {
                int ll = leftBefore + 1;
                int lr = leftBefore + leftCount;
                leftID = left.get(ll, lr);
            }
            if (rightCount > 0) {
                int rl = rightBefore + 1;
                int rr = rightBefore + rightCount;
                rightID = right.get(rl, rr);
            }

            int res;
            if (leftID == 0) res = rightID;
            else if (rightID == 0) res = leftID;
            else res = newSet(leftID, rightID);

            node.seg[base + (r - l)] = res;

            if (g_cnt > CNT_LIMIT) {
                // should not happen with chosen construction
                // still avoid undefined behavior
                // (printing partial output would be invalid anyway)
                exit(0);
            }
        }
    }

    return node;
}

struct BlockData {
    Node root;
    vector<int> posList; // positions of root.vals in increasing order
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    FastScanner fs;
    int n, q;
    if (!fs.readInt(n)) return 0;
    fs.readInt(q);

    vector<int> a(n + 1);
    vector<int> posOfValue(n + 1, 0);
    vector<int> idValue(n + 1, 0);

    for (int i = 1; i <= n; ++i) {
        fs.readInt(a[i]);
        posOfValue[a[i]] = i;
        idValue[a[i]] = i; // initial set id for value a[i] is i
    }

    g_cnt = n;
    g_ops.clear();
    g_ops.reserve(2100000);

    const int B = 256;
    int numBlocks = (n + B - 1) / B;
    vector<BlockData> blocks;
    blocks.reserve(numBlocks);

    for (int b = 0; b < numBlocks; ++b) {
        int L = b * B + 1;
        int R = min(n, (b + 1) * B);

        BlockData bd;
        bd.root = buildRange(L, R, posOfValue, idValue);

        bd.posList.resize(bd.root.s);
        for (int i = 0; i < bd.root.s; ++i) bd.posList[i] = posOfValue[bd.root.vals[i]];

        blocks.push_back(std::move(bd));
    }

    vector<int> ans(q);
    for (int qi = 0; qi < q; ++qi) {
        int l, r;
        fs.readInt(l);
        fs.readInt(r);

        int cur = 0;
        for (int bi = 0; bi < (int)blocks.size(); ++bi) {
            const auto &bd = blocks[bi];
            const auto &pl = bd.posList;

            auto itL = lower_bound(pl.begin(), pl.end(), l);
            auto itR = upper_bound(pl.begin(), pl.end(), r);
            if (itL == itR) continue;

            int pL = int(itL - pl.begin()) + 1;
            int pR = int(itR - pl.begin());
            int id = bd.root.get(pL, pR);

            if (cur == 0) cur = id;
            else cur = newSet(cur, id);

            if (g_cnt > CNT_LIMIT) exit(0);
        }
        ans[qi] = cur;
    }

    int cntE = n + (int)g_ops.size();
    if (cntE > CNT_LIMIT) exit(0);

    FastOutput fo;
    fo.writeInt(cntE);
    fo.writeChar('\n');
    for (auto &op : g_ops) {
        fo.writeInt(op.first);
        fo.writeChar(' ');
        fo.writeInt(op.second);
        fo.writeChar('\n');
    }
    for (int i = 0; i < q; ++i) {
        if (i) fo.writeChar(' ');
        fo.writeInt(ans[i]);
    }
    fo.writeChar('\n');
    fo.flush();
    return 0;
}