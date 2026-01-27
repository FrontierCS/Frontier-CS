#include <bits/stdc++.h>
using namespace std;

struct Node {
    int lch, rch;
    int setId;
    int lastL, lastR;
    Node(): lch(-1), rch(-1), setId(0), lastL(-1), lastR(-1) {}
};

struct BucketTree {
    int n;
    vector<Node> seg;
    int root;
    vector<int> leafNode;
    vector<pair<int,int>> *ops;
    int *pcnt;

    BucketTree() {}
    BucketTree(int nLeaves, vector<pair<int,int>> *ops_, int *pcnt_) {
        init(nLeaves, ops_, pcnt_);
    }
    void init(int nLeaves, vector<pair<int,int>> *ops_, int *pcnt_) {
        n = nLeaves;
        ops = ops_;
        pcnt = pcnt_;
        seg.clear();
        leafNode.assign(n, -1);
        root = build(0, n-1);
    }
    int newNode() {
        seg.emplace_back();
        return (int)seg.size()-1;
    }
    int build(int l, int r) {
        int id = newNode();
        if (l == r) {
            leafNode[l] = id;
        } else {
            int m = (l + r) >> 1;
            seg[id].lch = build(l, m);
            seg[id].rch = build(m+1, r);
        }
        return id;
    }
    inline int mergeSets(int L, int R) {
        // both L and R non-zero, and by construction value ranges disjoint and ordered
        ops->push_back({L, R});
        ++(*pcnt);
        return *pcnt;
    }
    int pull(int id) {
        int L = seg[id].lch == -1 ? 0 : seg[seg[id].lch].setId;
        int R = seg[id].rch == -1 ? 0 : seg[seg[id].rch].setId;
        if (L == 0 && R == 0) {
            if (seg[id].setId != 0) {
                seg[id].setId = 0;
            }
            seg[id].lastL = L; seg[id].lastR = R;
            return seg[id].setId;
        } else if (L == 0) {
            seg[id].setId = R;
            seg[id].lastL = L; seg[id].lastR = R;
            return seg[id].setId;
        } else if (R == 0) {
            seg[id].setId = L;
            seg[id].lastL = L; seg[id].lastR = R;
            return seg[id].setId;
        } else {
            if (seg[id].lastL == L && seg[id].lastR == R && seg[id].setId != 0) {
                return seg[id].setId;
            }
            int nid = mergeSets(L, R);
            seg[id].setId = nid;
            seg[id].lastL = L; seg[id].lastR = R;
            return seg[id].setId;
        }
    }
    int updateLeafRec(int id, int l, int r, int pos, int valSet) {
        if (l == r) {
            seg[id].setId = valSet;
            seg[id].lastL = 0; seg[id].lastR = 0; // leaf
            return seg[id].setId;
        }
        int m = (l + r) >> 1;
        if (pos <= m) updateLeafRec(seg[id].lch, l, m, pos, valSet);
        else updateLeafRec(seg[id].rch, m+1, r, pos, valSet);
        return pull(id);
    }
    int updateLeaf(int pos, int valSet) {
        if (n == 0) return 0;
        return updateLeafRec(root, 0, n-1, pos, valSet);
    }
    int rootSet() const { return seg[root].setId; }
};

struct PerBucketValueTree {
    int Lval, Rval; // inclusive values
    int size;
    vector<Node> seg;
    int root;
    vector<int> leafPos; // value -> leaf position index (0..size-1)
    vector<int> valList; // list of values in this bucket
    vector<pair<int,int>> *ops;
    int *pcnt;

    PerBucketValueTree() {}
    void init(int Lv, int Rv, vector<pair<int,int>> *ops_, int *pcnt_) {
        Lval = Lv; Rval = Rv;
        ops = ops_;
        pcnt = pcnt_;
        size = Rval - Lval + 1;
        valList.resize(size);
        for (int i = 0; i < size; ++i) valList[i] = Lval + i;
        leafPos.assign(Rval + 1, -1); // we'll only use indexes >= Lval
        seg.clear();
        root = build(0, size-1);
    }
    int newNode() {
        seg.emplace_back();
        return (int)seg.size() - 1;
    }
    int build(int l, int r) {
        int id = newNode();
        if (l == r) {
            int v = valList[l];
            if ((int)leafPos.size() <= v) leafPos.resize(v+1, -1);
            leafPos[v] = l;
        } else {
            int m = (l + r) >> 1;
            seg[id].lch = build(l, m);
            seg[id].rch = build(m+1, r);
        }
        return id;
    }
    inline int mergeSets(int L, int R) {
        ops->push_back({L, R});
        ++(*pcnt);
        return *pcnt;
    }
    int pull(int id) {
        int L = seg[id].lch == -1 ? 0 : seg[seg[id].lch].setId;
        int R = seg[id].rch == -1 ? 0 : seg[seg[id].rch].setId;
        if (L == 0 && R == 0) {
            if (seg[id].setId != 0) seg[id].setId = 0;
            seg[id].lastL = L; seg[id].lastR = R;
            return seg[id].setId;
        } else if (L == 0) {
            seg[id].setId = R;
            seg[id].lastL = L; seg[id].lastR = R;
            return seg[id].setId;
        } else if (R == 0) {
            seg[id].setId = L;
            seg[id].lastL = L; seg[id].lastR = R;
            return seg[id].setId;
        } else {
            if (seg[id].lastL == L && seg[id].lastR == R && seg[id].setId != 0) {
                return seg[id].setId;
            }
            int nid = mergeSets(L, R);
            seg[id].setId = nid;
            seg[id].lastL = L; seg[id].lastR = R;
            return seg[id].setId;
        }
    }
    int updateRec(int id, int l, int r, int pos, int valSet) {
        if (l == r) {
            seg[id].setId = valSet;
            seg[id].lastL = 0; seg[id].lastR = 0;
            return seg[id].setId;
        }
        int m = (l + r) >> 1;
        if (pos <= m) updateRec(seg[id].lch, l, m, pos, valSet);
        else updateRec(seg[id].rch, m+1, r, pos, valSet);
        return pull(id);
    }
    int setLeafByValue(int v, int valSet) {
        if (v < Lval || v > Rval) return seg[root].setId;
        int pos = leafPos[v];
        return updateRec(root, 0, size-1, pos, valSet);
    }
    int rootSet() const { return seg[root].setId; }
};

struct Query {
    int l, r, idx;
};
int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n, q;
    if (!(cin >> n >> q)) {
        return 0;
    }
    vector<int> a(n+1), posOfValue(n+1);
    for (int i = 1; i <= n; ++i) {
        cin >> a[i];
        posOfValue[a[i]] = i;
    }
    vector<Query> queries(q);
    for (int i = 0; i < q; ++i) {
        int l, r; cin >> l >> r;
        queries[i] = {l, r, i};
    }

    // Parameters
    int bucketSize = 64;
    if (bucketSize > n) bucketSize = n;
    int B = (n + bucketSize - 1) / bucketSize;

    // Prepare operations and count
    vector<pair<int,int>> ops;
    ops.reserve(2200000);
    int cnt = n; // initial sets S_i are the singletons {a_i}
    // Build per-bucket value trees
    vector<PerBucketValueTree> buckets(B);
    for (int b = 0; b < B; ++b) {
        int Lv = b * bucketSize + 1;
        int Rv = min(n, (b+1) * bucketSize);
        buckets[b].init(Lv, Rv, &ops, &cnt);
    }

    // Build bucket tree over B leaves
    BucketTree bucketTree(B, &ops, &cnt);

    // Mo's ordering
    int blockSize = max(1, (int)sqrt(n));
    sort(queries.begin(), queries.end(), [&](const Query &A, const Query &Bq) {
        int ab = A.l / blockSize;
        int bb = Bq.l / blockSize;
        if (ab != bb) return ab < bb;
        if (ab & 1) return A.r > Bq.r;
        else return A.r < Bq.r;
    });

    vector<int> presentValue(n+1, 0);
    auto addValue = [&](int v) {
        if (presentValue[v]) return;
        presentValue[v] = 1;
        int bidx = (v - 1) / bucketSize;
        int singletonSet = posOfValue[v]; // initial S_i id
        int newBucketSet = buckets[bidx].setLeafByValue(v, singletonSet);
        // update bucket tree leaf bidx
        bucketTree.updateLeaf(bidx, newBucketSet);
    };
    auto removeValue = [&](int v) {
        if (!presentValue[v]) return;
        presentValue[v] = 0;
        int bidx = (v - 1) / bucketSize;
        int newBucketSet = buckets[bidx].setLeafByValue(v, 0);
        bucketTree.updateLeaf(bidx, newBucketSet);
    };

    vector<int> ans(q, 0);
    int curL = 1, curR = 0;
    for (auto &qu : queries) {
        int L = qu.l, R = qu.r;
        while (curL > L) addValue(a[--curL]);
        while (curR < R) addValue(a[++curR]);
        while (curL < L) removeValue(a[curL++]);
        while (curR > R) removeValue(a[curR--]);
        ans[qu.idx] = bucketTree.rootSet();
        if (ans[qu.idx] == 0) {
            // As a fallback, create by merging singletons in increasing value to ensure non-zero (shouldn't happen)
            // collect values in [L..R]
            vector<int> vals;
            vals.reserve(R-L+1);
            for (int i = L; i <= R; ++i) vals.push_back(a[i]);
            sort(vals.begin(), vals.end());
            int cur = posOfValue[vals[0]];
            for (size_t i = 1; i < vals.size(); ++i) {
                int nxt = posOfValue[vals[i]];
                ops.push_back({cur, nxt});
                ++cnt;
                cur = cnt;
            }
            ans[qu.idx] = cur;
        }
    }

    // Output
    cout << cnt << '\n';
    for (auto &p : ops) {
        cout << p.first << ' ' << p.second << '\n';
    }
    for (int i = 0; i < q; ++i) {
        if (i) cout << ' ';
        cout << ans[i];
    }
    cout << '\n';
    return 0;
}