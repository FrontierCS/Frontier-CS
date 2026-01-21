#include <bits/stdc++.h>
using namespace std;

struct Node {
    int lo, hi;
    int left, right;
    vector<int> pref; // pref[i] = number of elements <= mid among first i elements
    unordered_map<uint64_t, int> memo; // key: (l,r) packed into 64-bit, value: set ID
};

int n, q;
vector<int> a, invPos;
vector<Node> nodes;
vector<pair<int,int>> ops;
int cntSets;

inline uint64_t packKey(int l, int r) {
    return ( (uint64_t) (uint32_t) l << 32 ) | (uint32_t) r;
}

int buildWavelet(int lo, int hi, const vector<int> &arr) {
    Node nd;
    nd.lo = lo; nd.hi = hi;
    int m = (int)arr.size();
    nd.pref.resize(m + 1);
    if (lo == hi) {
        nd.left = nd.right = 0;
        nd.pref[0] = 0;
        for (int i = 1; i <= m; ++i) nd.pref[i] = nd.pref[i-1]; // no left/right split needed
        nodes.push_back(move(nd));
        return (int)nodes.size() - 1;
    } else {
        int mid = (lo + hi) >> 1;
        nd.pref[0] = 0;
        vector<int> L, R;
        L.reserve(m);
        R.reserve(m);
        for (int i = 0; i < m; ++i) {
            if (arr[i] <= mid) {
                L.push_back(arr[i]);
                nd.pref[i+1] = nd.pref[i] + 1;
            } else {
                R.push_back(arr[i]);
                nd.pref[i+1] = nd.pref[i];
            }
        }
        int leftId = buildWavelet(lo, mid, L);
        int rightId = buildWavelet(mid + 1, hi, R);
        nd.left = leftId;
        nd.right = rightId;
        nodes.push_back(move(nd));
        return (int)nodes.size() - 1;
    }
}

int buildSegmentSet(int nodeId, int l, int r) {
    if (l > r) return 0;
    Node &nd = nodes[nodeId];
    uint64_t key = packKey(l, r);
    auto it = nd.memo.find(key);
    if (it != nd.memo.end()) return it->second;

    int res = 0;
    if (nd.lo == nd.hi) {
        // leaf node: value is nd.lo, singleton set is S_{position where a[pos] == value}
        res = invPos[nd.lo];
        nd.memo.emplace(key, res);
        return res;
    } else {
        // map to children
        int lL = nd.pref[l-1] + 1;
        int rL = nd.pref[r];
        int lR = (l - 1) - nd.pref[l-1] + 1;
        int rR = r - nd.pref[r];

        int idL = 0, idR = 0;
        if (rL >= lL) idL = buildSegmentSet(nd.left, lL, rL);
        if (rR >= lR) idR = buildSegmentSet(nd.right, lR, rR);

        if (idL && idR) {
            ops.emplace_back(idL, idR);
            ++cntSets;
            res = cntSets;
        } else if (idL) {
            res = idL;
        } else if (idR) {
            res = idR;
        } else {
            res = 0; // should not happen for l<=r and non-empty node
        }
        nd.memo.emplace(key, res);
        return res;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    cin >> n >> q;
    a.resize(n+1);
    invPos.assign(n+1, 0);
    for (int i = 1; i <= n; ++i) {
        cin >> a[i];
        invPos[a[i]] = i; // value -> initial set ID (index)
    }
    vector<pair<int,int>> queries(q);
    for (int i = 0; i < q; ++i) {
        int l, r;
        cin >> l >> r;
        queries[i] = {l, r};
    }

    // Build wavelet tree on values of a[1..n]
    nodes.reserve(4 * n + 5);
    nodes.push_back(Node()); // dummy at index 0 to make nodes 1-based
    vector<int> rootArr(n);
    for (int i = 0; i < n; ++i) rootArr[i] = a[i+1];
    int rootId = buildWavelet(1, n, rootArr);

    cntSets = n;
    vector<int> ans(q);
    for (int i = 0; i < q; ++i) {
        int l = queries[i].first;
        int r = queries[i].second;
        ans[i] = buildSegmentSet(rootId, l, r);
    }

    int cntE = cntSets;
    cout << cntE << '\n';
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