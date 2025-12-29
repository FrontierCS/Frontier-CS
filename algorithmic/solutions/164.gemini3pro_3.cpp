#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Problem constants
// Although N=200 and M=10 are fixed in the problem description,
// we will use variables to accommodate the input.
int N_val, M_val;

// State of the warehouse
// stacks[i] contains the boxes in stack i, from bottom to top.
vector<int> stacks[15]; // M is up to 10, using 15 for safety

// To record the sequence of operations
struct Operation {
    int v, i;
};
vector<Operation> ans;

// Helper to find the current position of a box
struct Pos {
    int stack_idx;
    int height_idx; // 0-based index in the stack
};

Pos find_box(int v) {
    for (int i = 1; i <= M_val; ++i) {
        for (int j = 0; j < stacks[i].size(); ++j) {
            if (stacks[i][j] == v) {
                return {i, j};
            }
        }
    }
    return {-1, -1};
}

// Perform Operation 1: Move box v and all above it to stack i
void op1(int v, int i) {
    Pos p = find_box(v);
    int src = p.stack_idx;
    int idx = p.height_idx;
    
    // Identify the chunk to move
    vector<int> chunk;
    for (int k = idx; k < stacks[src].size(); ++k) {
        chunk.push_back(stacks[src][k]);
    }
    
    // Remove from source stack
    stacks[src].resize(idx);
    
    // Add to destination stack
    for (int x : chunk) {
        stacks[i].push_back(x);
    }
    
    // Record operation
    ans.push_back({v, i});
}

// Perform Operation 2: Carry out box v (must be at top)
void op2(int v) {
    Pos p = find_box(v);
    // Remove from stack
    stacks[p.stack_idx].pop_back();
    // Record operation
    ans.push_back({v, 0});
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N_val >> M_val)) return 0;
    
    // Read initial configuration
    for (int i = 1; i <= M_val; ++i) {
        for (int j = 0; j < N_val / M_val; ++j) {
            int val;
            cin >> val;
            stacks[i].push_back(val);
        }
    }

    // Main logic: Retrieve boxes 1 to N sequentially
    for (int target = 1; target <= N_val; ++target) {
        while (true) {
            Pos p = find_box(target);
            int src = p.stack_idx;
            int idx = p.height_idx;
            
            // If the target box is already at the top, we can carry it out.
            if (idx == stacks[src].size() - 1) {
                op2(target);
                break;
            }
            
            // The target box is buried. We need to move boxes above it.
            // Boxes to move are from index (idx + 1) to top.
            // We look for the best move strategy.
            // A move is defined by a split point 'k' (idx+1 <= k < size) and a destination 'dst'.
            // This moves the chunk stacks[src][k...end] to stacks[dst].
            
            int best_k = -1;
            int best_dst = -1;
            long long best_score = -2e18; // Initialize with a very low score
            
            bool found_valid = false;
            
            for (int k = idx + 1; k < stacks[src].size(); ++k) {
                int chunk_bottom_val = stacks[src][k];
                int chunk_size = (int)stacks[src].size() - k;
                
                for (int dst = 1; dst <= M_val; ++dst) {
                    if (dst == src) continue;
                    
                    bool is_empty = stacks[dst].empty();
                    // If empty, effectively top value is infinity (represented by 1000 here since N=200)
                    int dst_top = is_empty ? 1000 : stacks[dst].back();
                    
                    // A move is considered "valid" (heuristically good) if we place smaller value on larger value.
                    // This preserves the sorted order needed for future retrievals.
                    bool valid = (chunk_bottom_val < dst_top);
                    
                    if (valid) {
                        found_valid = true;
                        long long score = 0;
                        
                        // Heuristic Scoring:
                        // 1. Maximize chunk size. Moving larger chunks is more energy efficient per box.
                        //    Weight: Very High.
                        score += (long long)chunk_size * 100000000;
                        
                        // 2. Prefer non-empty stacks. Empty stacks are valuable resources (buffers).
                        //    Weight: High (but less than increasing chunk size by 1).
                        if (!is_empty) {
                            score += 50000000;
                            
                            // 3. Tightness. Minimize the gap between destination top and chunk bottom.
                            //    This keeps values packed closely, saving space for larger values elsewhere.
                            //    Weight: Low.
                            int diff = dst_top - chunk_bottom_val;
                            score -= diff; 
                        } else {
                            // Empty stack is valid, but gets no bonus.
                        }
                        
                        if (score > best_score) {
                            best_score = score;
                            best_k = k;
                            best_dst = dst;
                        }
                    }
                }
            }
            
            if (found_valid) {
                // Execute the best valid move found
                op1(stacks[src][best_k], best_dst);
            } else {
                // No valid moves exist (all possible moves create inversions or no empty stacks available).
                // We are forced to make a suboptimal move.
                // Strategy: Move the entire pile above target to the stack with the largest top value.
                // Moving the entire pile minimizes the number of operations (energy).
                // Choosing largest top minimizes the "severity" of the inversion (gap).
                
                int move_k = idx + 1; // Move everything above target
                int best_bad_dst = -1;
                int max_top = -1;
                
                for (int dst = 1; dst <= M_val; ++dst) {
                    if (dst == src) continue;
                    // stacks[dst] cannot be empty here (otherwise found_valid would be true)
                    int val = stacks[dst].back();
                    if (val > max_top) {
                        max_top = val;
                        best_bad_dst = dst;
                    }
                }
                
                // Fallback if something weird happens (should not with N=200, M=10)
                if (best_bad_dst == -1) best_bad_dst = (src % M_val) + 1;
                
                op1(stacks[src][move_k], best_bad_dst);
            }
        }
    }
    
    // Output the recorded sequence of operations
    for (const auto& m : ans) {
        cout << m.v << " " << m.i << "\n";
    }

    return 0;
}