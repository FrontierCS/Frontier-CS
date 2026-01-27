#include <bits/stdc++.h>
using namespace std;

struct Node {
    int lo, hi;
    int lch = -1, rch = -1;
    vector<int> pref; // pref[i] = number of elements <= mid in first i elements
    unordered_map<unsigned long long, int> memo; // key = (l<<32) | r
};

int n, q;
vector<int> a; // 1-indexed values a[1..n]
vector<int> posOfVal; // posOfVal[val] = index where a[index] = val
vector<Node> tree;
vector<pair<int,int>> ops;
int cnt; // current number of sets (initially n)

int build(int lo, int hi, const vector<int>& v) {
    int id = (int)tree.size();
    tree.push_back(Node());
    Node &nd = tree.back();
    nd.lo = lo;
    nd.hi = hi;
    int m = (int)v.size();
    nd.pref.resize(m + 1);
    nd.pref[0] = 0;

    if (lo == hi || m == 0) {
        // Leaf or empty node
        return id;
    }
    int mid = (lo + hi) >> 1;
    vector<int> L, R;
    L.reserve(m);
    R.reserve(m);
    for (int i = 0; i < m; ++i) {
        nd.pref[i+1] = nd.pref[i] + (v[i] <= mid);
        if (v[i] <= mid) L.push_back(v[i]);
        else R.push_back(v[i]);
    }
    if (!L.empty()) nd.lch = build(lo, mid, L);
    if (!R.empty()) nd.rch = build(mid + 1, hi, R);
    return id;
}

inline unsigned long long keyLR(int l, int r) {
    return ( (unsigned long long) (unsigned int) l << 32 ) | (unsigned int) r;
}

int merge_sets(int u, int v) {
    ops.emplace_back(u, v);
    ++cnt;
    return cnt;
}

int getSet(int nodeId, int l, int r) {
    Node &nd = tree[nodeId];
    unsigned long long key = keyLR(l, r);
    auto it = nd.memo.find(key);
    if (it != nd.memo.end()) return it->second;

    if (nd.lo == nd.hi) {
        // Leaf node: the set is just the singleton of this value
        int id = posOfVal[nd.lo]; // base set ID is the original index
        nd.memo.emplace(key, id);
        return id;
    }

    int leftCount = nd.pref[r] - nd.pref[l-1];
    int total = r - l + 1;
    int rightCount = total - leftCount;

    if (leftCount == 0) {
        int lR = l - nd.pref[l-1];
        int rR = r - nd.pref[r];
        int res = getSet(nd.rch, lR, rR);
        nd.memo.emplace(key, res);
        return res;
    } else if (rightCount == 0) {
        int lL = nd.pref[l-1] + 1;
        int rL = nd.pref[r];
        int res = getSet(nd.lch, lL, rL);
        nd.memo.emplace(key, res);
        return res;
    } else {
        int lL = nd.pref[l-1] + 1;
        int rL = nd.pref[r];
        int lR = l - nd.pref[l-1];
        int rR = r - nd.pref[r];
        int leftId = getSet(nd.lch, lL, rL);
        int rightId = getSet(nd.rch, lR, rR);
        int res = merge_sets(leftId, rightId);
        nd.memo.emplace(key, res);
        return res;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    cin >> n >> q;
    a.resize(n + 1);
    for (int i = 1; i <= n; ++i) cin >> a[i];
    posOfVal.assign(n + 1, 0);
    for (int i = 1; i <= n; ++i) posOfVal[a[i]] = i;

    vector<int> vals(n);
    for (int i = 0; i < n; ++i) vals[i] = a[i+1];

    tree.reserve(4 * n);
    int root = build(1, n, vals);

    cnt = n;
    vector<pair<int,int>> queries(q);
    for (int i = 0; i < q; ++i) {
        int l, r; cin >> l >> r;
        queries[i] = {l, r};
    }
    vector<int> ans(q);
    for (int i = 0; i < q; ++i) {
        int l = queries[i].first;
        int r = queries[i].second;
        ans[i] = getSet(root, l, r);
    }

    cout << cnt << '\n';
    for (auto &op : ops) {
        cout << op.first << ' ' << op.second << '\n';
    }
    for (int i = 0; i < q; ++i) {
        if (i) cout << ' ';
        cout << ans[i];
    }
    cout << '\n';
    return 0;
}