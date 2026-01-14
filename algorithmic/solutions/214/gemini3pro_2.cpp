#include <iostream>
#include <vector>
#include <algorithm>
#include <map>
#include <queue>
#include <numeric>

using namespace std;

// Structure to store operations
struct Op {
    int l, r;
};

// Global variables for best solution
int best_x = -1;
vector<Op> best_ops;
int min_ops_count = 1e9;

int n_global;
vector<int> a_global;

// Apply reversal to a permutation
void apply_op(vector<int>& p, int l, int r) {
    reverse(p.begin() + l - 1, p.begin() + r);
}

// Solve for a specific x
void solve(int x) {
    if (x + 1 > n_global) return;
    
    vector<int> p = a_global;
    vector<Op> current_ops;
    
    // Phase 1: Place n, n-1, ..., x+2
    // We want to sort the suffix.
    // Target positions: n, n-1, ...
    
    // Position map for optimization
    vector<int> pos(n_global + 1);
    for (int i = 0; i < n_global; ++i) pos[p[i]] = i + 1;
    
    for (int k = n_global; k >= x + 2; --k) {
        // We want to bring value k to position k
        int curr = pos[k];
        
        if (curr == k) continue;
        
        // Step 1: Bring curr into prefix 1..x+1 if it's not there (and not at k)
        // Since we process k decreasing, elements > k are already fixed.
        // curr must be <= k.
        // If curr > x+1, we can jump left by x.
        while (curr > x + 1) {
            // Apply Rev(curr - x, curr)
            // This moves element at curr to curr - x
            int l = curr - x;
            int r = curr;
            current_ops.push_back({l, r});
            
            // Update permutation and pos array efficiently?
            // Reversing full segment is slow O(x). Total O(N^2). OK for N=1000.
            apply_op(p, l, r);
            // Rebuild pos map for affected elements
            for (int i = l; i <= r; ++i) pos[p[i-1]] = i;
            
            curr = pos[k];
        }
        
        // Now curr is in 1..x+1.
        // We want to jump to k.
        // The jumps are of length x+1, i.e., Rev(u, u+x) moves u -> u+x?
        // Let's trace Rev(u, u+x):
        // Indices u ... u+x.
        // Element at u moves to u+x.
        // We need to land at k.
        // So final jump is to k. Start of jump: k-x.
        // Chain: k <- k-x <- k-2x ...
        // Target in prefix is S such that S <= x+1 and S = k - m*x.
        // S = (k - 1) % x + 1.
        // Exception: if S=1 and we need to move 1->1+x, we use Rev(1, 1+x).
        
        int target_s = (k - 1) % x + 1;
        
        // Move curr to target_s within 1..x+1
        // Using shifts and flips on 1..x+1.
        // Since x is small (3,5,7), we can just use BFS to move curr to target_s
        // while preserving the set of elements in 1..x+1 (just permuting them).
        // Actually, simpler: BFS to find sequence of operations on 1..x+1 
        // that moves element at curr to target_s.
        // We don't care about other elements in 1..x+1.
        
        // BFS state: position of our element.
        // Transitions: 
        // 1. Shift by 2 (Rev(1, x+1) then Rev(3, x+1) -> moves i to i-2 cyclically?)
        // Let's just use the available reversals starting at 1..
        // Available ops inside 1..x+1:
        // Rev(1, x+1)
        // Rev(1, x-1), Rev(2, x), Rev(3, x+1) -> length x-1
        
        while (curr != target_s) {
            // Greedy or BFS for one step?
            // Just BFS for shortest path to target_s
            queue<pair<int, int>> q;
            q.push({curr, -1}); // pos, type
            // type: 0 = Rev(1, x+1), 1 = Rev(1, x-1), 2 = Rev(2, x), ...
            // Encode op: L << 16 | R
            
            vector<int> parent(x + 2, 0);
            vector<int> op_record(x + 2, 0);
            vector<bool> visited(x + 2, false);
            visited[curr] = true;
            
            int found_pos = -1;
            
            while(!q.empty()){
                int u = q.front().first;
                q.pop();
                
                if (u == target_s) {
                    found_pos = u;
                    break;
                }
                
                // Try all valid ops in 1..x+1
                // 1. Length x+1: Rev(1, x+1)
                {
                    int v = (1 + x + 1) - u; // Map u to 1+(x+1)-u
                    if (!visited[v]) {
                        visited[v] = true;
                        parent[v] = u;
                        op_record[v] = (1 << 16) | (x + 1);
                        q.push({v, -1});
                    }
                }
                // 2. Length x-1: Rev(s, s+x-2) where 1 <= s and s+x-2 <= x+1
                // s can be 1, 2, 3
                for (int s = 1; s <= 3; ++s) {
                    int e = s + x - 2;
                    if (e > x + 1) continue;
                    // Check if u is in range
                    int v = u;
                    if (u >= s && u <= e) {
                        v = s + e - u;
                    }
                    if (!visited[v]) {
                        visited[v] = true;
                        parent[v] = u;
                        op_record[v] = (s << 16) | e;
                        q.push({v, -1});
                    }
                }
            }
            
            // Reconstruct ONE step or full path?
            // Reconstruct full path
            vector<pair<int,int>> path_ops;
            int iter = target_s;
            while(iter != curr) {
                int code = op_record[iter];
                path_ops.push_back({code >> 16, code & 0xFFFF});
                iter = parent[iter];
            }
            reverse(path_ops.begin(), path_ops.end());
            
            for (auto op : path_ops) {
                current_ops.push_back({op.first, op.second});
                apply_op(p, op.first, op.second);
                // rebuild pos
                for(int i=1; i<=x+1; ++i) pos[p[i-1]] = i;
            }
            curr = pos[k]; // Should be target_s
        }
        
        // Now curr == target_s.
        // Jump to k
        while (curr + x <= k) {
            int l = curr;
            int r = curr + x;
            current_ops.push_back({l, r});
            apply_op(p, l, r);
            // Optimization: only update relevant pos
             pos[p[l-1]] = l;
             pos[p[r-1]] = r; 
             // Actually, full reverse changes all inside.
             // But we only care about k.
             // Element k moves from l to r.
             // Other elements are swapped.
             // Just full update is safer and fast enough.
            for (int i = l; i <= r; ++i) pos[p[i-1]] = i;
            
            curr += x;
        }
    }
    
    // Phase 2: Sort remaining 1..x+1
    // Use BFS. State is vector<int>.
    // Since x is small (up to 7 -> size 8), BFS is feasible.
    // For x=7, size 8, 8! = 40320 states.
    
    int m = x + 1;
    vector<int> sub(m);
    for(int i=0; i<m; ++i) sub[i] = p[i];
    
    vector<int> sorted_sub = sub;
    sort(sorted_sub.begin(), sorted_sub.end());
    
    // Check if already sorted
    bool sorted = true;
    for(int i=0; i<m; ++i) if(sub[i] != sorted_sub[i]) sorted = false;
    
    if (!sorted) {
        map<vector<int>, pair<int, int>> dist; // state -> {parent_move_encoded, parent_state_hash?}
        // Storing parent state is heavy. 
        // Better: map<vector<int>, pair<vector<int>, pair<int,int>>> pred;
        map<vector<int>, pair<vector<int>, pair<int,int>>> parent;
        
        queue<vector<int>> q;
        q.push(sub);
        parent[sub] = { {}, {-1, -1} };
        
        vector<int> final_state;
        bool found = false;
        
        while(!q.empty()){
            vector<int> u = q.front();
            q.pop();
            
            if (u == sorted_sub) {
                final_state = u;
                found = true;
                break;
            }
            
            // Try operations
            // Length m (x+1) -> [1, m]
            // Length m-2 (x-1) -> [1, m-2], [2, m-1], [3, m]
            
            // Op 1: 1..m
            {
                vector<int> v = u;
                reverse(v.begin(), v.end());
                if (parent.find(v) == parent.end()) {
                    parent[v] = {u, {1, m}};
                    q.push(v);
                }
            }
            
            // Op 2: len m-2
            int len2 = m - 2;
            for (int s = 1; s <= 3; ++s) {
                int e = s + len2 - 1;
                if (e > m) continue;
                vector<int> v = u;
                reverse(v.begin() + s - 1, v.begin() + e);
                if (parent.find(v) == parent.end()) {
                    parent[v] = {u, {s, e}};
                    q.push(v);
                }
            }
        }
        
        // Reconstruct path
        if (found) {
            vector<pair<int,int>> path;
            vector<int> curr_state = final_state;
            while(curr_state != sub) {
                auto pr = parent[curr_state];
                path.push_back(pr.second);
                curr_state = pr.first;
            }
            reverse(path.begin(), path.end());
            for(auto op : path) {
                current_ops.push_back({op.first, op.second});
            }
        } else {
            // Should not happen for solvable sizes
            // If happens, x is invalid
            current_ops.clear();
            // Penalty
            for(int i=0;i<1000000;++i) current_ops.push_back({1,2});
        }
    }
    
    if (current_ops.size() < min_ops_count) {
        min_ops_count = current_ops.size();
        best_x = x;
        best_ops = current_ops;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    if (!(cin >> n_global)) return 0;
    a_global.resize(n_global);
    for (int i = 0; i < n_global; ++i) cin >> a_global[i];
    
    // Candidates for x
    // Small odd values.
    // If N is small, just try N-1 (if odd) or similar.
    vector<int> candidates;
    if (n_global <= 8) {
        for (int x = 1; x < n_global; x += 2) candidates.push_back(x);
    } else {
        candidates = {3, 5, 7}; // 7 is usually best for N large
    }
    
    // If n_global is small, 7 might be too big
    vector<int> valid_candidates;
    for (int x : candidates) {
        if (x + 1 <= n_global) valid_candidates.push_back(x);
    }
    
    if (valid_candidates.empty()) {
        // Fallback for very small N (e.g. N=2 -> x=1)
        valid_candidates.push_back(1); 
    }
    
    for (int x : valid_candidates) {
        solve(x);
    }
    
    cout << best_x << "\n";
    cout << best_ops.size() << "\n";
    for (const auto& op : best_ops) {
        cout << op.l << " " << op.r << "\n";
    }
    
    return 0;
}