#include <iostream>
#include <vector>
#include <algorithm>
#include <map>
#include <queue>
#include <numeric>

using namespace std;

// Operation structure
struct Op {
    int l, r, dir; // dir 0: left, 1: right
};

int n;
vector<int> a;
vector<Op> ops;
int x;

// Apply operation to array
void apply_op(vector<int>& arr, int l, int r, int dir) {
    // 1-based indexing in l, r
    // arr is 0-based, so indices are l-1 to r-1
    int start = l - 1;
    int end = r - 1;
    int len = end - start + 1;
    if (len < 1) return;
    
    if (dir == 0) { // Left shift
        int first = arr[start];
        for (int i = start; i < end; ++i) {
            arr[i] = arr[i+1];
        }
        arr[end] = first;
    } else { // Right shift
        int last = arr[end];
        for (int i = end; i > start; --i) {
            arr[i] = arr[i-1];
        }
        arr[start] = last;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n)) return 0;
    a.resize(n);
    for (int i = 0; i < n; ++i) {
        cin >> a[i];
    }

    // Heuristic choice for x
    // If n is small, we pick x = n-1 to allow movements.
    // If n is large, x=14 provides a good balance between phase 1 efficiency and phase 2 complexity.
    if (n <= 15) {
        x = n - 1;
        if (x < 1) x = 1; 
    } else {
        x = 14;
    }
    
    if (n == 1) {
        cout << "1 0\n";
        return 0;
    }

    // Phase 1: Sort 1 to n - (x + 1)
    // We sort elements one by one until the unsorted suffix has size x + 1.
    int limit = n - (x + 1);
    if (limit < 0) limit = 0;

    for (int i = 1; i <= limit; ++i) {
        // Find current position of value i
        int pos = -1;
        for (int k = 0; k < n; ++k) {
            if (a[k] == i) {
                pos = k + 1; // 1-based
                break;
            }
        }
        
        // Move to i using jumps (Right Shift on [pos-x+1, pos])
        // This moves element at pos to pos-x+1
        while (pos >= i + x - 1) {
            int l = pos - x + 1;
            int r = pos;
            ops.push_back({l, r, 1}); // Right shift
            apply_op(a, l, r, 1);
            pos = l;
        }
        
        // Move to i using steps (Left Shift on [i, i+x-1])
        // This moves element at pos (which is > i) to pos-1
        // We use the range [i, i+x-1] because we know pos is inside (i, i+x-1]
        // and shifting this range doesn't disturb 1..i-1.
        while (pos > i) {
            int l = i;
            int r = i + x - 1;
            ops.push_back({l, r, 0}); // Left shift
            apply_op(a, l, r, 0);
            pos--;
        }
    }

    // Phase 2: Sort the remaining suffix using Bi-directional BFS
    int suffix_start = limit; // 0-based index
    int suffix_len = n - suffix_start;
    
    if (suffix_len > 0) {
        vector<int> suffix;
        for (int i = suffix_start; i < n; ++i) suffix.push_back(a[i]);
        
        vector<int> target = suffix;
        sort(target.begin(), target.end());
        
        if (suffix != target) {
            int num_offsets = suffix_len - x + 1;
            
            // Maps for BFS: state -> distance
            map<vector<int>, int> dist_start;
            // map: state -> (move_index, parent_state)
            // move_index = offset * 2 + direction
            map<vector<int>, pair<int, vector<int>>> parent_start;
            
            map<vector<int>, int> dist_end;
            map<vector<int>, pair<int, vector<int>>> parent_end;
            
            queue<vector<int>> q_start, q_end;
            
            dist_start[suffix] = 0;
            q_start.push(suffix);
            
            dist_end[target] = 0;
            q_end.push(target);
            
            vector<int> meet_state;
            bool met = false;
            
            // Limit states to prevent TLE, though with x=14, suffix=15, it should be fast
            int max_states = 600000;
            int count = 0;
            
            while (!q_start.empty() || !q_end.empty()) {
                if (met) break;
                if (count > max_states) break;
                
                // Expand from start
                if (!q_start.empty()) {
                    vector<int> u = q_start.front();
                    q_start.pop();
                    
                    if (dist_end.count(u)) {
                        meet_state = u;
                        met = true;
                        break;
                    }
                    
                    // Depth limit for one side
                    if (dist_start[u] >= 11) continue; 
                    
                    for (int off = 0; off < num_offsets; ++off) {
                        for (int d = 0; d < 2; ++d) { // 0: Left, 1: Right
                            vector<int> v = u;
                            int l = off;
                            int r = off + x - 1;
                            if (d == 0) { // Left
                                int first = v[l];
                                for (int k = l; k < r; ++k) v[k] = v[k+1];
                                v[r] = first;
                            } else { // Right
                                int last = v[r];
                                for (int k = r; k > l; --k) v[k] = v[k-1];
                                v[l] = last;
                            }
                            
                            if (!dist_start.count(v)) {
                                dist_start[v] = dist_start[u] + 1;
                                parent_start[v] = {off * 2 + d, u};
                                q_start.push(v);
                                count++;
                            }
                        }
                    }
                }
                
                // Expand from end (inverse ops)
                if (!q_end.empty()) {
                    vector<int> u = q_end.front();
                    q_end.pop();
                    
                    if (dist_start.count(u)) {
                        meet_state = u;
                        met = true;
                        break;
                    }
                    
                    if (dist_end[u] >= 11) continue;
                    
                    for (int off = 0; off < num_offsets; ++off) {
                        for (int d = 0; d < 2; ++d) { 
                            // We are moving backwards from target to start
                            // So if the forward move was 'd', the backward move is inverse of 'd'.
                            // However, we want to find the forward move sequence.
                            // The edge in the graph is bidirectional.
                            // If we came from u to v via op 'd', then v to u is via inv(d).
                            // Here we explore neighbors v of u via op 'd' in the move space (reverse logic).
                            // Wait, strictly speaking: BFS from End generates states reachable from Target by Inverse Ops.
                            // A state v in End-search with parent u via op D means: v -> u via D.
                            // So if we find match, we trace back.
                            
                            // Let's perform inverse op to generate previous state
                            int inv_d = 1 - d;
                            vector<int> v = u;
                            int l = off;
                            int r = off + x - 1;
                            if (inv_d == 0) { // Inverse is Left
                                int first = v[l];
                                for (int k = l; k < r; ++k) v[k] = v[k+1];
                                v[r] = first;
                            } else { // Inverse is Right
                                int last = v[r];
                                for (int k = r; k > l; --k) v[k] = v[k-1];
                                v[l] = last;
                            }
                            
                            if (!dist_end.count(v)) {
                                dist_end[v] = dist_end[u] + 1;
                                parent_end[v] = {off * 2 + d, u}; // Store the FORWARD move d
                                q_end.push(v);
                                count++;
                            }
                        }
                    }
                }
            }
            
            if (met) {
                vector<pair<int, int>> path_moves;
                
                // Path from start to meet
                vector<int> curr = meet_state;
                while (curr != suffix) {
                    auto p = parent_start[curr];
                    int move = p.first;
                    path_moves.push_back({move / 2, move % 2});
                    curr = p.second;
                }
                reverse(path_moves.begin(), path_moves.end());
                
                // Path from meet to target
                // parent_end stores (move, parent). The parent is closer to target.
                // state v -> u via move D.
                // We are at meet_state. Trace to target.
                curr = meet_state;
                while (curr != target) {
                    auto p = parent_end[curr];
                    int move = p.first;
                    path_moves.push_back({move / 2, move % 2});
                    curr = p.second;
                }
                
                for (auto p : path_moves) {
                    int off = p.first;
                    int d = p.second;
                    int l = suffix_start + 1 + off;
                    int r = l + x - 1;
                    ops.push_back({l, r, d});
                }
            }
        }
    }

    cout << x << " " << ops.size() << "\n";
    for (const auto& op : ops) {
        cout << op.l << " " << op.r << " " << op.dir << "\n";
    }

    return 0;
}