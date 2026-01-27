#include <bits/stdc++.h>
using namespace std;

struct Node {
    int lo, hi;
    vector<int> pref; // pref[i] = number of elements <= mid among first i elements (1-based indexing for positions)
    Node *left = nullptr, *right = nullptr;
    int m; // size of sequence at this node
};

int n, q;
vector<int> a, posIdx;
vector<pair<int,int>> ops;
int nextId;

// Build wavelet tree
Node* build(const vector<int> &arr, int lo, int hi) {
    Node* node = new Node();
    node->lo = lo; node->hi = hi;
    node->m = (int)arr.size();
    node->pref.assign(node->m + 1, 0);
    if (node->m == 0) return node;
    if (lo == hi) {
        // leaf
        // pref not needed beyond zero initialization
        return node;
    }
    int mid = (lo + hi) >> 1;
    vector<int> leftArr; leftArr.reserve(node->m);
    vector<int> rightArr; rightArr.reserve(node->m);
    for (int i = 0; i < node->m; ++i) {
        node->pref[i+1] = node->pref[i] + (arr[i] <= mid);
        if (arr[i] <= mid) leftArr.push_back(arr[i]);
        else rightArr.push_back(arr[i]);
    }
    if (!leftArr.empty()) node->left = build(leftArr, lo, mid);
    if (!rightArr.empty()) node->right = build(rightArr, mid+1, hi);
    return node;
}

// Merge two sets (ids u and v), ensuring u corresponds to left value range and v to right value range
inline int new_merge(int u, int v) {
    ops.emplace_back(u, v);
    return ++nextId;
}

// Combine two intervals [l1,r1] and [l2,r2] within node's sequence (1-based indices). Returns set id or 0 if empty.
int combineIntervals(Node* node, int l1, int r1, int l2, int r2) {
    if (!node) return 0;
    bool e1 = (l1 > r1);
    bool e2 = (l2 > r2);
    if (e1 && e2) return 0;
    if (node->lo == node->hi) {
        // leaf contains single value node->lo, which appears exactly once in original array
        // If any interval includes it, return its initial singleton set id = index position
        return posIdx[node->lo];
    }
    int mid = (node->lo + node->hi) >> 1;

    auto map_to_children = [&](int l, int r, int &lL, int &rL, int &lR, int &rR) {
        if (l > r) { lL = 1; rL = 0; lR = 1; rR = 0; return; }
        int pl1 = node->pref[l-1];
        int pr1 = node->pref[r];
        lL = pl1 + 1;
        rL = pr1;
        lR = l - pl1;
        rR = r - pr1;
    };

    int l1L, r1L, l1R, r1R;
    int l2L, r2L, l2R, r2R;
    map_to_children(l1, r1, l1L, r1L, l1R, r1R);
    map_to_children(l2, r2, l2L, r2L, l2R, r2R);

    int leftSet = 0, rightSet = 0;
    if (node->left) {
        leftSet = combineIntervals(node->left, l1L, r1L, l2L, r2L);
    }
    if (node->right) {
        rightSet = combineIntervals(node->right, l1R, r1R, l2R, r2R);
    }

    if (leftSet == 0) return rightSet;
    if (rightSet == 0) return leftSet;
    return new_merge(leftSet, rightSet);
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    cin >> n >> q;
    a.resize(n+1);
    for (int i = 1; i <= n; ++i) cin >> a[i];
    posIdx.assign(n+1, 0);
    for (int i = 1; i <= n; ++i) posIdx[a[i]] = i;

    // Build wavelet tree on the whole array values
    vector<int> arr(n);
    for (int i = 0; i < n; ++i) arr[i] = a[i+1];
    Node* root = build(arr, 1, n);

    vector<pair<int,int>> queries(q);
    for (int i = 0; i < q; ++i) {
        int l, r; cin >> l >> r;
        queries[i] = {l, r};
    }

    nextId = n; // initial sets are 1..n

    // Precompute floor log2 up to n
    vector<int> lg(n+1, 0);
    for (int i = 2; i <= n; ++i) lg[i] = lg[i>>1] + 1;

    vector<int> ans(q, 0);

    for (int i = 0; i < q; ++i) {
        int l = queries[i].first;
        int r = queries[i].second;
        if (l == r) {
            ans[i] = l; // S_l = {a_l}
            continue;
        }
        int len = r - l + 1;
        int k = lg[len];
        int b = 1 << k;
        int l1 = l, r1 = l + b - 1;
        int l2 = r - b + 1, r2 = r;

        // The union [l1,r1] U [l2,r2] equals [l,r]
        int setId = combineIntervals(root, l1, r1, l2, r2);
        ans[i] = setId;
    }

    // Output
    int cntE = nextId;
    cout << cntE << "\n";
    for (auto &p : ops) {
        cout << p.first << " " << p.second << "\n";
    }
    for (int i = 0; i < q; ++i) {
        if (i) cout << " ";
        cout << ans[i];
    }
    cout << "\n";
    return 0;
}