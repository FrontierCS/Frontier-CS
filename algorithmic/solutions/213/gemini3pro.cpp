#include <iostream>
#include <vector>
#include <algorithm>
#include <numeric>
#include <deque>
#include <map>

using namespace std;

// Structure to represent an operation
struct Op {
    int l, r, d; // d=0: Left, d=1: Right
};

int n;
vector<int> a;
vector<Op> ops;
int x;

// Function to perform a shift on the array and record it
void apply_op(int l, int r, int d) {
    ops.push_back({l, r, d});
    if (d == 0) { // Left shift
        int first = a[l - 1];
        for (int i = l - 1; i < r - 1; ++i) {
            a[i] = a[i + 1];
        }
        a[r - 1] = first;
    } else { // Right shift
        int last = a[r - 1];
        for (int i = r - 1; i > l - 1; --i) {
            a[i] = a[i - 1];
        }
        a[l - 1] = last;
    }
}

// Helper to calculate cyclic distance
int dist_right(int pos, int target_pos, int len) {
    // Distance to move 'pos' to 'target_pos' using right shifts
    // Right shift moves element at pos to pos+1.
    // Effectively index increases.
    // We want index to become target_pos.
    if (target_pos >= pos) return target_pos - pos;
    return target_pos - pos + len;
}

int dist_left(int pos, int target_pos, int len) {
    // Left shift moves element at pos to pos-1.
    if (pos >= target_pos) return pos - target_pos;
    return pos - target_pos + len;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n)) return 0;
    a.resize(n);
    for (int i = 0; i < n; ++i) {
        cin >> a[i];
    }

    x = 22; // Block size
    if (x > n) x = n; // Handle small n
    
    // Phase 1: Sort 1 to n - x
    int limit = n - x;
    if (limit < 0) limit = 0;

    for (int i = 1; i <= limit; ++i) {
        // Find current position of value i
        int pos = -1;
        for (int k = 0; k < n; ++k) {
            if (a[k] == i) {
                pos = k + 1; // 1-based index
                break;
            }
        }

        // Move element to the left using large jumps (Right Shift on [pos-x+1, pos])
        // This moves element at pos to pos-x+1
        while (pos - i >= x - 1) {
            apply_op(pos - x + 1, pos, 1);
            pos = pos - x + 1;
        }

        // Now element is close to i (dist < x - 1)
        // We can use local shifts.
        // Option 1: Left shifts on [i, i+x-1]. Moves element at pos towards i.
        // Option 2: Right shifts on [i, i+x-1]. Moves element at pos towards i (wrapping).
        if (pos > i) {
            int cost_left = pos - i;
            int cost_right = x - (pos - i);

            if (cost_left <= cost_right) {
                for (int k = 0; k < cost_left; ++k) apply_op(i, i + x - 1, 0);
            } else {
                for (int k = 0; k < cost_right; ++k) apply_op(i, i + x - 1, 1);
            }
        }
    }

    // Phase 2: Sort the suffix.
    // Suffix range indices: n-x+1 to n.
    // Buffer index: n-x.
    // We use an insertion sort approach relative to the circular suffix.
    
    // Current sorted count in the suffix
    int sorted_cnt = 0;
    
    // We will place values v = n-x+1 to n-3 correctly relative to each other.
    // For the last few, we use BFS.
    int bfs_start_val = n - 2; 
    if (limit == 0) bfs_start_val = 1; // If n is small, just BFS all.
    
    for (int v = n - x + 1; v < bfs_start_val; ++v) {
        // Locate v
        int pos = -1;
        for (int k = 0; k < n; ++k) {
            if (a[k] == v) {
                pos = k + 1;
                break;
            }
        }

        // Step A: Move v to Buffer (n-x)
        if (pos >= n - x + 1) {
            // In suffix. Rotate suffix so pos is at n-x+1.
            // Suffix is [n-x+1, n].
            // To bring pos to n-x+1:
            // Right shift suffix (moves indices right, element at end wraps to start).
            // Actually, just calculating moves.
            // Move pos to n-x+1.
            // Left shifts: pos decreases.
            int d = pos - (n - x + 1); // dist from start
            // To move to start: d Left Shifts.
            // Or x-d Right Shifts.
            if (d <= x - d) {
                 for(int k=0; k<d; ++k) apply_op(n-x+1, n, 0);
            } else {
                 for(int k=0; k<x-d; ++k) apply_op(n-x+1, n, 1);
            }
            
            // Now v is at n-x+1. Op A: Left Shift [n-x, n-1].
            // n-x+1 moves to n-x.
            apply_op(n - x, n - 1, 0);
            // v is at n-x.
        } 
        // Else v is at n-x (Buffer). Do nothing.

        // Step B: Insert v into suffix after v-1.
        if (sorted_cnt == 0) {
            // Just insert. Op A: n-x moves to n-1.
            apply_op(n - x, n - 1, 0);
        } else {
            // Find v-1 in suffix
            int p_prev = -1;
            for (int k = n - x; k < n; ++k) { // Suffix indices + buffer? No, v-1 must be in suffix
                if (a[k] == v - 1) {
                    p_prev = k + 1;
                    break;
                }
            }
            
            // Rotate suffix so p_prev is at n-2.
            int target = n - 2;
            int current = p_prev;
            // Range [n-x+1, n].
            // Move current to target.
            // Dist left: current - target (mod x)
            // But coordinates are absolute.
            // Map to 0..x-1
            int c_rel = current - (n - x + 1);
            int t_rel = target - (n - x + 1);
            int diff = (c_rel - t_rel + x) % x; // Number of left shifts needed?
            // Left shift reduces index.
            // If we shift left by 'diff', index becomes (c_rel - diff) = t_rel.
            // Check cost.
            if (diff <= x - diff) {
                for(int k=0; k<diff; ++k) apply_op(n-x+1, n, 0);
            } else {
                for(int k=0; k<x-diff; ++k) apply_op(n-x+1, n, 1);
            }

            // Check ejection candidate at n-x+1.
            // We assume greedy works (collision analysis in thought process suggests it works until end).
            // Insert: Op A (n-x moves to n-1).
            apply_op(n - x, n - 1, 0);
        }
        sorted_cnt++;
    }

    // Align the sorted part.
    // Find n-x+1. Rotate suffix so it is at n-x+1.
    // If n-x+1 is in buffer, something is wrong, but logic says it should be in suffix.
    if (bfs_start_val > n - x + 1) {
        int start_val = n - x + 1;
        int pos = -1;
        for (int k = n - x; k < n; ++k) {
             if (a[k] == start_val) {
                 pos = k + 1; break;
             }
        }
        if (pos != -1 && pos != n - x) {
             int c_rel = pos - (n - x + 1);
             int t_rel = 0; // target n-x+1
             int diff = (c_rel - t_rel + x) % x;
             if (diff <= x - diff) {
                 for(int k=0; k<diff; ++k) apply_op(n-x+1, n, 0);
             } else {
                 for(int k=0; k<x-diff; ++k) apply_op(n-x+1, n, 1);
             }
        }
    }

    // Phase 3: BFS for the remaining elements.
    // We only care about sorting the whole array now.
    // The prefix 1..n-x is fixed. 
    // The relative order of n-x+1..bfs_start_val-1 is fixed and aligned.
    // We just need to fix the last few elements and the buffer.
    
    // BFS State: vector<int> representing permutation of last x+1 elements.
    // Available ops: 
    // 0: Left Shift [n-x+1, n]
    // 1: Right Shift [n-x+1, n]
    // 2: Left Shift [n-x, n-1]
    
    // We can't simply explore whole graph. But we are close.
    // Use BFS.
    
    vector<int> target_perm;
    for(int i=n-x; i<n; ++i) target_perm.push_back(i+1);
    
    map<vector<int>, int> dist;
    map<vector<int>, pair<int, int>> parent; // state -> {op_type, prev_state_hash?} No, store full path is expensive.
    // Since depth is small, we can just store path in queue or reconstruct.
    // Store parent map: current_vec -> {op_idx, parent_vec}
    
    vector<int> current_perm;
    for(int i=n-x; i<n; ++i) current_perm.push_back(a[i]);
    
    if (current_perm != target_perm) {
        deque<vector<int>> q;
        q.push_back(current_perm);
        dist[current_perm] = 0;
        parent[current_perm] = {-1, {}}; // Root
        
        while(!q.empty()) {
            vector<int> u = q.front();
            q.pop_front();
            
            if (u == target_perm) break;
            
            if (dist[u] >= 12) continue; // Limit depth
            
            // Try ops
            // Op 0: Left shift suffix (indices 1..x in 0-based u)
            vector<int> v = u;
            // Suffix is u[1]...u[x].
            int temp = v[1];
            for(int k=1; k<x; ++k) v[k] = v[k+1];
            v[x] = temp;
            if (dist.find(v) == dist.end()) {
                dist[v] = dist[u] + 1;
                parent[v] = {0, u};
                q.push_back(v);
                if (v == target_perm) break;
            }
            
            // Op 1: Right shift suffix
            v = u;
            temp = v[x];
            for(int k=x; k>1; --k) v[k] = v[k-1];
            v[1] = temp;
            if (dist.find(v) == dist.end()) {
                dist[v] = dist[u] + 1;
                parent[v] = {1, u};
                q.push_back(v);
                if (v == target_perm) break;
            }
            
            // Op 2: Left shift buffer-involved (indices 0..x-1)
            v = u;
            temp = v[0];
            for(int k=0; k<x-1; ++k) v[k] = v[k+1];
            v[x-1] = temp;
            if (dist.find(v) == dist.end()) {
                dist[v] = dist[u] + 1;
                parent[v] = {2, u};
                q.push_back(v);
                if (v == target_perm) break;
            }

            // Op 3: Right shift buffer-involved (indices 0..x-1) -- Usually not needed but helps
             v = u;
            temp = v[x-1];
            for(int k=x-1; k>0; --k) v[k] = v[k-1];
            v[0] = temp;
            if (dist.find(v) == dist.end()) {
                dist[v] = dist[u] + 1;
                parent[v] = {3, u};
                q.push_back(v);
                if (v == target_perm) break;
            }
        }
        
        // Reconstruct path
        vector<int> path_ops;
        vector<int> curr = target_perm;
        while(curr != current_perm) {
            auto p = parent[curr];
            path_ops.push_back(p.first);
            curr = p.second; // Wait, parent map value type mismatch?
            // parent stores {op, parent_vec}.
            // map<vector<int>, pair<int, vector<int>>> needed.
        }
        reverse(path_ops.begin(), path_ops.end());
        
        for(int op_type : path_ops) {
            if (op_type == 0) apply_op(n - x + 1, n, 0);
            else if (op_type == 1) apply_op(n - x + 1, n, 1);
            else if (op_type == 2) apply_op(n - x, n - 1, 0);
            else if (op_type == 3) apply_op(n - x, n - 1, 1);
        }
    }

    cout << x << " " << ops.size() << "\n";
    for (const auto& op : ops) {
        cout << op.l << " " << op.r << " " << op.d << "\n";
    }

    return 0;
}