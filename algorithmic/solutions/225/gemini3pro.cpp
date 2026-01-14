#include <iostream>
#include <vector>
#include <algorithm>
#include <map>

using namespace std;

// Global variables to store problem data and results
int n, q;
int cnt; // Current number of sets
vector<pair<int, int>> ops; // List of operations (u, v) for merging Su and Sv
vector<int> a; // The permutation
vector<int> pos_in_perm; // pos_in_perm[v] is the index i such that a[i] = v. 1-based.

// Solves the problem for a range of values [v_L, v_R]
// p: The positions (indices in permutation) of the values in [v_L, v_R], sorted.
// reqs: A list of unique requested intervals [u, v] relative to p.
// Returns: A vector of set IDs corresponding to the requests in 'reqs'.
vector<int> solve(int v_L, int v_R, const vector<int>& p, vector<pair<int, int>>& reqs) {
    if (reqs.empty()) return {};

    // Base case: leaf node (single value)
    if (v_L == v_R) {
        vector<int> res;
        res.reserve(reqs.size());
        // For a single value, the only valid non-empty range on p (which has size 1) is [0, 0].
        // The set corresponding to this value is the initial set S_{pos_in_perm[v_L]}.
        int set_id = pos_in_perm[v_L]; 
        for (const auto& r : reqs) {
            // In a leaf, r should be {0, 0} because we prune empty requests.
            res.push_back(set_id);
        }
        return res;
    }

    int mid = v_L + (v_R - v_L) / 2;
    
    // Split p into p_left (values <= mid) and p_right (values > mid)
    // and build prefix counts to map indices.
    vector<int> p_left, p_right;
    p_left.reserve(p.size());
    p_right.reserve(p.size());

    // cnt_L[i] stores how many elements in p[0...i-1] went to left child
    vector<int> cnt_L(p.size() + 1, 0);
    vector<int> cnt_R(p.size() + 1, 0);
    
    for (size_t i = 0; i < p.size(); ++i) {
        int val = a[p[i]];
        if (val <= mid) {
            p_left.push_back(p[i]);
            cnt_L[i+1] = cnt_L[i] + 1;
            cnt_R[i+1] = cnt_R[i];
        } else {
            p_right.push_back(p[i]);
            cnt_L[i+1] = cnt_L[i];
            cnt_R[i+1] = cnt_R[i] + 1;
        }
    }

    // Prepare requests for children
    // reqs_L_raw and reqs_R_raw correspond 1-to-1 with reqs
    vector<pair<int, int>> reqs_L_raw, reqs_R_raw;
    reqs_L_raw.reserve(reqs.size());
    reqs_R_raw.reserve(reqs.size());
    
    for (const auto& r : reqs) {
        int u = r.first;
        int v = r.second;
        
        // Map interval [u, v] to left child
        int u_L = cnt_L[u];
        int v_L_idx = cnt_L[v+1] - 1;
        if (u_L <= v_L_idx) {
            reqs_L_raw.push_back({u_L, v_L_idx});
        } else {
            reqs_L_raw.push_back({-1, -1}); // Mark as empty/invalid
        }
        
        // Map interval [u, v] to right child
        int u_R = cnt_R[u];
        int v_R_idx = cnt_R[v+1] - 1;
        if (u_R <= v_R_idx) {
            reqs_R_raw.push_back({u_R, v_R_idx});
        } else {
            reqs_R_raw.push_back({-1, -1});
        }
    }
    
    // Create unique sorted requests for recursion
    vector<pair<int, int>> reqs_L_unique = reqs_L_raw;
    vector<pair<int, int>> reqs_R_unique = reqs_R_raw;
    
    sort(reqs_L_unique.begin(), reqs_L_unique.end());
    reqs_L_unique.erase(unique(reqs_L_unique.begin(), reqs_L_unique.end()), reqs_L_unique.end());
    
    sort(reqs_R_unique.begin(), reqs_R_unique.end());
    reqs_R_unique.erase(unique(reqs_R_unique.begin(), reqs_R_unique.end()), reqs_R_unique.end());
    
    // Remove the invalid marker if present (it will be at the beginning)
    if (!reqs_L_unique.empty() && reqs_L_unique[0].first == -1) {
        reqs_L_unique.erase(reqs_L_unique.begin());
    }
    if (!reqs_R_unique.empty() && reqs_R_unique[0].first == -1) {
        reqs_R_unique.erase(reqs_R_unique.begin());
    }
    
    // Recursive calls
    vector<int> res_L_ids = solve(v_L, mid, p_left, reqs_L_unique);
    vector<int> res_R_ids = solve(mid + 1, v_R, p_right, reqs_R_unique);
    
    // Helper to find ID for a request
    auto get_id = [](const vector<pair<int, int>>& unique_reqs, const vector<int>& ids, pair<int, int> req) -> int {
        if (req.first == -1) return -1;
        auto it = lower_bound(unique_reqs.begin(), unique_reqs.end(), req);
        int idx = distance(unique_reqs.begin(), it);
        return ids[idx];
    };
    
    vector<int> res_ids;
    res_ids.reserve(reqs.size());
    
    // Memoize merges performed at this node to avoid creating duplicate sets locally
    map<pair<int, int>, int> merge_memo;
    
    for (size_t i = 0; i < reqs.size(); ++i) {
        int id_L = get_id(reqs_L_unique, res_L_ids, reqs_L_raw[i]);
        int id_R = get_id(reqs_R_unique, res_R_ids, reqs_R_raw[i]);
        
        if (id_L == -1 && id_R == -1) {
            // This should not happen for initially valid non-empty queries
            res_ids.push_back(-1);
        } else if (id_L == -1) {
            res_ids.push_back(id_R);
        } else if (id_R == -1) {
            res_ids.push_back(id_L);
        } else {
            // Both exist, need to merge
            if (merge_memo.count({id_L, id_R})) {
                res_ids.push_back(merge_memo[{id_L, id_R}]);
            } else {
                cnt++;
                ops.push_back({id_L, id_R});
                merge_memo[{id_L, id_R}] = cnt;
                res_ids.push_back(cnt);
            }
        }
    }
    
    return res_ids;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> q)) return 0;
    
    a.resize(n + 1);
    pos_in_perm.resize(n + 1);
    for (int i = 1; i <= n; ++i) {
        cin >> a[i];
        pos_in_perm[a[i]] = i;
    }
    
    vector<pair<int, int>> initial_reqs(q);
    // Initial position vector p contains 1..n (indices of permutation)
    vector<int> p(n);
    for (int i = 0; i < n; ++i) p[i] = i + 1;
    
    for (int i = 0; i < q; ++i) {
        int l, r;
        cin >> l >> r;
        // Convert to 0-based indices for our internal logic
        initial_reqs[i] = {l - 1, r - 1};
    }
    
    cnt = n; // Initial sets are 1..n
    
    // Process unique requests at root to potentially save time
    vector<pair<int, int>> unique_reqs = initial_reqs;
    sort(unique_reqs.begin(), unique_reqs.end());
    unique_reqs.erase(unique(unique_reqs.begin(), unique_reqs.end()), unique_reqs.end());
    
    // Solve
    vector<int> unique_ids = solve(1, n, p, unique_reqs);
    
    // Output results
    cout << cnt << "\n";
    for (const auto& op : ops) {
        cout << op.first << " " << op.second << "\n";
    }
    
    // Map back to original query order
    for (int i = 0; i < q; ++i) {
        auto it = lower_bound(unique_reqs.begin(), unique_reqs.end(), initial_reqs[i]);
        int idx = distance(unique_reqs.begin(), it);
        cout << unique_ids[idx] << (i == q - 1 ? "" : " ");
    }
    cout << "\n";
    
    return 0;
}