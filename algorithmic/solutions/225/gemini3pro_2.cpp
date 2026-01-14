#include <iostream>
#include <vector>
#include <map>

using namespace std;

// Global variables to store the problem inputs and outputs
int n, q;
vector<int> a;
vector<int> pos_of_val;
int current_cnt;
vector<pair<int, int>> operations;

// Wavelet Tree Node structure
struct Node {
    int val_L, val_R;
    // to_left[k] stores how many elements in the first k elements (of this node's range)
    // go to the left child.
    vector<int> to_left;
    // Memoization map to store result IDs for ranges [i, j]
    // Key is encoded as (i << 12) | j
    map<int, int> memo;
} tree[20000]; // Array size sufficient for N <= 4096 (approx 2*N nodes)

// Function to build the Wavelet Tree
void build(int u, int vl, int vr, const vector<int>& indices) {
    tree[u].val_L = vl;
    tree[u].val_R = vr;
    
    if (vl == vr) {
        return;
    }
    
    int mid = vl + (vr - vl) / 2;
    vector<int> left_indices;
    left_indices.reserve(indices.size());
    vector<int> right_indices;
    right_indices.reserve(indices.size());
    
    tree[u].to_left.resize(indices.size() + 1, 0);
    
    for (size_t i = 0; i < indices.size(); ++i) {
        int idx = indices[i];
        if (a[idx] <= mid) {
            left_indices.push_back(idx);
            tree[u].to_left[i+1] = tree[u].to_left[i] + 1;
        } else {
            right_indices.push_back(idx);
            tree[u].to_left[i+1] = tree[u].to_left[i];
        }
    }
    
    build(2 * u, vl, mid, left_indices);
    build(2 * u + 1, mid + 1, vr, right_indices);
}

// Function to query the Wavelet Tree and construct sets
// Returns the ID of the set corresponding to indices in range [i, j] of current node's P vector
int query(int u, int i, int j) {
    // Unique key for the range [i, j]
    // Since N <= 4096, 12 bits are enough for j.
    int key = (i << 12) | j;
    
    if (tree[u].memo.count(key)) {
        return tree[u].memo[key];
    }
    
    // Leaf case
    if (tree[u].val_L == tree[u].val_R) {
        // A leaf represents a single value 'val'.
        // The set should be {val}, which corresponds to the initial set S_{pos_of_val[val] + 1}.
        int val = tree[u].val_L;
        int initial_idx = pos_of_val[val];
        return tree[u].memo[key] = initial_idx + 1;
    }
    
    // Internal node
    // Map the range [i, j] to sub-ranges for left and right children
    int l_cnt_before = tree[u].to_left[i];
    int l_cnt_total = tree[u].to_left[j+1];
    
    int l_start = l_cnt_before;
    int l_end = l_cnt_total - 1;
    
    int r_start = i - l_cnt_before;
    int r_end = j - l_cnt_total;
    
    int left_res = 0;
    if (l_start <= l_end) {
        left_res = query(2 * u, l_start, l_end);
    }
    
    int right_res = 0;
    if (r_start <= r_end) {
        right_res = query(2 * u + 1, r_start, r_end);
    }
    
    if (left_res != 0 && right_res != 0) {
        // Merge the two sets.
        // Left set contains values <= mid.
        // Right set contains values > mid.
        // So max(left_res) < min(right_res), valid merge.
        current_cnt++;
        operations.push_back({left_res, right_res});
        return tree[u].memo[key] = current_cnt;
    } else if (left_res != 0) {
        return tree[u].memo[key] = left_res;
    } else {
        return tree[u].memo[key] = right_res;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> n >> q)) return 0;
    
    a.resize(n);
    pos_of_val.resize(n + 1);
    vector<int> initial_indices(n);
    for (int i = 0; i < n; ++i) {
        cin >> a[i];
        pos_of_val[a[i]] = i; // Map value to its index in permutation
        initial_indices[i] = i;
    }
    
    current_cnt = n; // Initial sets are 1..n
    
    // Build the wavelet tree
    build(1, 1, n, initial_indices);
    
    vector<int> results(q);
    for (int k = 0; k < q; ++k) {
        int l, r;
        cin >> l >> r;
        --l; --r; // Convert to 0-based
        results[k] = query(1, l, r);
    }
    
    cout << current_cnt << "\n";
    for (const auto& op : operations) {
        cout << op.first << " " << op.second << "\n";
    }
    for (int k = 0; k < q; ++k) {
        cout << results[k] << (k == q - 1 ? "" : " ");
    }
    cout << "\n";
    
    return 0;
}