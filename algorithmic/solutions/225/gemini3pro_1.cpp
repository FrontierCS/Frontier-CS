#include <iostream>
#include <vector>
#include <algorithm>
#include <map>

using namespace std;

// Constraints: N <= 4096. 
// Tree nodes: 4 * 4096 is enough (approx 16384).
const int MAXN = 4105;
const int MAX_NODES = 16384; 

int n, q;
int a[MAXN];
int pos[MAXN]; // pos[v] = index i such that a[i] = v

// Merge Sort Tree structures
// tree_p[u] stores the sorted list of original indices (positions) for values in the range covered by node u
vector<int> tree_p[MAX_NODES]; 
// to_left[u][i] stores how many elements in tree_p[u][0...i-1] go to the left child
vector<int> to_left[MAX_NODES]; 
// Memoization for set IDs. Key is (s << 12) | e, Value is set ID.
map<int, int> memo[MAX_NODES]; 

int cnt; // Current number of sets
vector<pair<int, int>> operations; // Stores the merge operations

// Build the Merge Sort Tree
// u: current node index, [vl, vr]: value range
void build(int u, int vl, int vr) {
    if (vl == vr) {
        tree_p[u].push_back(pos[vl]);
        return;
    }
    int mid = (vl + vr) / 2;
    build(2 * u, vl, mid);
    build(2 * u + 1, mid + 1, vr);

    // Merge sorted vectors from children to form current node's vector
    const auto& left_p = tree_p[2 * u];
    const auto& right_p = tree_p[2 * u + 1];
    
    int i = 0, j = 0;
    to_left[u].push_back(0);
    while (i < left_p.size() || j < right_p.size()) {
        bool pick_left = false;
        if (i < left_p.size() && j < right_p.size()) {
            if (left_p[i] < right_p[j]) pick_left = true;
        } else if (i < left_p.size()) {
            pick_left = true;
        }
        
        if (pick_left) {
            tree_p[u].push_back(left_p[i]);
            i++;
            to_left[u].push_back(to_left[u].back() + 1);
        } else {
            tree_p[u].push_back(right_p[j]);
            j++;
            to_left[u].push_back(to_left[u].back());
        }
    }
}

// Get set ID for the subset of values in range [vl, vr] that are at positions tree_p[u][s...e]
// u: current node, [vl, vr]: value range, [s, e]: indices in tree_p[u]
int solve(int u, int vl, int vr, int s, int e) {
    if (s > e) return 0;
    
    // Check memoization
    // s and e are bounded by N <= 4096, so we can pack them into an integer key
    int key = (s << 12) | e;
    if (memo[u].count(key)) return memo[u][key];
    
    if (vl == vr) {
        // Leaf node: value range [vl, vl].
        // tree_p[u] contains only pos[vl], so s=0, e=0.
        // We need the set corresponding to value vl.
        // Initially we have sets S_i = {a_i}. Since a[pos[vl]] = vl, S_{pos[vl]} = {vl}.
        return memo[u][key] = pos[vl];
    }
    
    int mid = (vl + vr) / 2;
    
    // Map range [s, e] from current node to left child
    // Number of elements going to left before index s
    int s_L = to_left[u][s];
    // Number of elements going to left up to index e (inclusive) -> corresponding end index is count - 1
    int e_L = to_left[u][e + 1] - 1;
    
    // Map range [s, e] to right child
    // Index in right child corresponds to (original_index - number_of_left_elements_before_it)
    int s_R = s - to_left[u][s];
    int e_R = e + 1 - to_left[u][e + 1] - 1;
    
    int id_L = solve(2 * u, vl, mid, s_L, e_L);
    int id_R = solve(2 * u + 1, mid + 1, vr, s_R, e_R);
    
    int res = 0;
    if (id_L && id_R) {
        // Both sets exist, merge them.
        // Condition: max(S_L) < min(S_R).
        // Since id_L comes from values [vl, mid] and id_R from [mid+1, vr],
        // all elements in S_L are <= mid and all in S_R are >= mid+1. Condition holds.
        cnt++;
        operations.push_back({id_L, id_R});
        res = cnt;
    } else if (id_L) {
        res = id_L;
    } else if (id_R) {
        res = id_R;
    }
    
    return memo[u][key] = res;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> n >> q)) return 0;
    
    for (int i = 1; i <= n; ++i) {
        cin >> a[i];
        pos[a[i]] = i;
    }
    
    build(1, 1, n);
    
    cnt = n; // Initial sets are 1..n
    
    vector<int> query_results(q);
    for (int i = 0; i < q; ++i) {
        int l, r;
        cin >> l >> r;
        // The root node (1) corresponds to sorted positions of all values.
        // Since all values 1..n are present, tree_p[1] contains positions 1, 2, ..., n in order.
        // Thus, the query range [l, r] (1-based indices) corresponds to indices l-1 to r-1 in tree_p[1].
        query_results[i] = solve(1, 1, n, l - 1, r - 1);
    }
    
    cout << cnt << "\n";
    for (const auto& op : operations) {
        cout << op.first << " " << op.second << "\n";
    }
    for (int i = 0; i < q; ++i) {
        cout << query_results[i] << (i == q - 1 ? "" : " ");
    }
    cout << "\n";
    
    return 0;
}