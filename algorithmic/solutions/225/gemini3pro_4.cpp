#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Node structure for the Value Segment Tree
// This tree is built over the VALUES of the permutation.
// Each node represents a range of values [val_l, val_r].
// It stores a list P of indices from the original permutation such that a[index] is in [val_l, val_r].
struct Node {
    int id; // Node index in the tree vector
    int val_l, val_r; // Value range covered by this node
    int left_child = -1, right_child = -1;
    vector<int> P; // List of indices (positions in permutation) that have values in [val_l, val_r]
    vector<int> to_left; // rank array: to_left[i] = count of elements in P[0...i-1] going to left child
    vector<int> memo; // Memoization table for range queries on P
    
    // Helper to compute index for memoization of range [l, r]
    // l and r are indices into P, so 0 <= l <= r < P.size()
    // We map the pair (l, r) to a single integer index.
    inline int get_memo_idx(int l, int r, int sz) {
        // Row l has length sz - l.
        // Offset for row l is sum_{k=0}^{l-1} (sz - k) = l*sz - l*(l-1)/2
        // Index within row is r - l
        return l * sz - (l * (l - 1)) / 2 + (r - l);
    }
};

int n, q;
vector<int> a;
vector<Node> tree;
vector<pair<int, int>> operations; // Stores pairs of (u, v) for merge operations
int current_cnt; // Current number of sets

// Build the Value Tree
// u: current node index
// vl, vr: value range
void build(int u, int vl, int vr) {
    tree[u].val_l = vl;
    tree[u].val_r = vr;
    int sz = tree[u].P.size();
    
    // Allocate memoization table
    // Number of subsegments is sz * (sz + 1) / 2
    // With N=4096, this fits in memory.
    long long memo_sz = (long long)sz * (sz + 1) / 2;
    tree[u].memo.assign(memo_sz, -1);

    if (vl == vr) {
        return;
    }

    int mid = vl + (vr - vl) / 2;
    
    // Create children
    int l_node = tree.size();
    tree.emplace_back(); tree.back().id = l_node;
    int r_node = tree.size();
    tree.emplace_back(); tree.back().id = r_node;

    tree[u].left_child = l_node;
    tree[u].right_child = r_node;

    tree[u].to_left.resize(sz + 1, 0);
    
    // Partition P into left and right children based on values
    // This stable partitioning allows us to map range queries to children.
    for (int i = 0; i < sz; ++i) {
        tree[u].to_left[i+1] = tree[u].to_left[i];
        int val = a[tree[u].P[i]-1]; // Value at the position P[i]
        if (val <= mid) {
            tree[l_node].P.push_back(tree[u].P[i]);
            tree[u].to_left[i+1]++;
        } else {
            tree[r_node].P.push_back(tree[u].P[i]);
        }
    }

    build(l_node, vl, mid);
    build(r_node, mid + 1, vr);
}

// Solve for set corresponding to P[l...r] at node u
// This returns the ID of a set containing { a[k] | k in P[l...r] }
int solve(int u, int l, int r) {
    if (l > r) return 0;
    
    // Base case: leaf node in Value Tree
    // Represents a single value. P contains just the position of that value.
    if (tree[u].val_l == tree[u].val_r) {
        // Return the initial set ID for this position.
        // Initial sets are 1..n, where S_k = {a_k}.
        // P[l] stores the index k.
        return tree[u].P[l];
    }

    // Check memoization
    int sz = tree[u].P.size();
    int memo_idx = tree[u].get_memo_idx(l, r, sz);
    if (tree[u].memo[memo_idx] != -1) {
        return tree[u].memo[memo_idx];
    }

    // Determine the corresponding ranges in left and right children
    // Left child range:
    int l_l = tree[u].to_left[l]; 
    int l_r = tree[u].to_left[r+1] - 1; 
    
    // Right child range:
    // Number of elements going right before index l is l - tree[u].to_left[l]
    int start_right = l - tree[u].to_left[l];
    // Number of elements in range [l, r] going to right child
    int cnt_left = tree[u].to_left[r+1] - tree[u].to_left[l];
    int cnt_right = (r - l + 1) - cnt_left;
    
    int set_l = 0;
    if (l_l <= l_r) {
        set_l = solve(tree[u].left_child, l_l, l_r);
    }
    
    int set_r = 0;
    if (cnt_right > 0) {
        set_r = solve(tree[u].right_child, start_right, start_right + cnt_right - 1);
    }
    
    int res = 0;
    if (set_l != 0 && set_r != 0) {
        // Merge operation
        // Left child values are all <= mid, Right child values are all > mid.
        // So max(S_L) <= mid < min(S_R). Condition g(S_u) < f(S_v) satisfied.
        current_cnt++;
        operations.push_back({set_l, set_r});
        res = current_cnt;
    } else if (set_l != 0) {
        res = set_l;
    } else {
        res = set_r;
    }
    
    return tree[u].memo[memo_idx] = res;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> n >> q)) return 0;
    
    a.resize(n);
    for (int i = 0; i < n; ++i) {
        cin >> a[i];
    }
    
    // Reserve memory to prevent reallocation issues
    tree.reserve(2 * n + 100);
    
    // Create root node
    tree.emplace_back(); 
    tree.back().id = 0; 
    // Initial indices at root are 1 to n
    for (int i = 1; i <= n; ++i) tree[0].P.push_back(i);
    
    build(0, 1, n);
    
    current_cnt = n; // Initially n sets S_1...S_n
    vector<int> results(q);
    
    for (int i = 0; i < q; ++i) {
        int l, r;
        cin >> l >> r;
        // Queries are 1-based [l, r].
        // Root P contains 1..n. P[k] = k+1.
        // We need the range of indices in P that corresponds to positions l..r.
        // Indices in P are 0-based.
        // l maps to index l-1, r maps to index r-1.
        results[i] = solve(0, l - 1, r - 1);
    }
    
    cout << current_cnt << "\n";
    for (auto &op : operations) {
        cout << op.first << " " << op.second << "\n";
    }
    for (int i = 0; i < q; ++i) {
        cout << results[i] << (i == q - 1 ? "" : " ");
    }
    cout << "\n";
    
    return 0;
}