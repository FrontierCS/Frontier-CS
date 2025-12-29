#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Structure to store the operations
struct Op {
    int v;
    int i;
};

int main() {
    // Optimization for faster I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n, m;
    if (!(cin >> n >> m)) return 0;

    // Stacks are 1-indexed to match the problem statement's output format (1 to m)
    // 0 is used for the "carry out" operation destination
    vector<vector<int>> stacks(m + 1);
    
    // Read the initial configuration of boxes
    // Each stack has exactly n/m boxes initially
    for (int i = 1; i <= m; ++i) {
        for (int j = 0; j < n / m; ++j) {
            int b;
            cin >> b;
            stacks[i].push_back(b);
        }
    }

    vector<Op> ops;
    int current_target = 1;

    // Main loop to process boxes from 1 to n
    while (current_target <= n) {
        int s_idx = -1;
        int b_idx = -1;
        
        // Locate the current target box
        for (int i = 1; i <= m; ++i) {
            for (int j = 0; j < stacks[i].size(); ++j) {
                if (stacks[i][j] == current_target) {
                    s_idx = i;
                    b_idx = j;
                    break;
                }
            }
            if (s_idx != -1) break;
        }

        // If the target box is at the top of its stack, carry it out
        if (b_idx == stacks[s_idx].size() - 1) {
            ops.push_back({current_target, 0});
            stacks[s_idx].pop_back();
            current_target++;
            continue;
        }

        // If not at the top, we need to move the boxes above it to other stacks.
        // We look for the best "chunk" of boxes to move from the top of the stack.
        // A chunk is defined by the number of boxes from the top (sz).
        
        int boxes_above = stacks[s_idx].size() - 1 - b_idx;
        
        int best_sz = -1;
        int best_dst = -1;
        long long best_score = -2e18; // Initialize with a very low score

        // Iterate through all possible chunk sizes we can move
        for (int sz = 1; sz <= boxes_above; ++sz) {
            int start_pos = stacks[s_idx].size() - sz;
            
            // Find the maximum value in this chunk to determine if it fits nicely
            int chunk_max = -1;
            for (int k = 0; k < sz; ++k) {
                chunk_max = max(chunk_max, stacks[s_idx][start_pos + k]);
            }

            // Evaluate all possible destination stacks
            for (int dst = 1; dst <= m; ++dst) {
                if (dst == s_idx) continue; // Cannot move to the same stack

                // Determine the value at the top of the destination stack
                // If empty, treat it as having a very large value (1000)
                int top_val = (stacks[dst].empty()) ? 1000 : stacks[dst].back();
                
                long long score;
                
                // Heuristic Scoring Logic
                if (chunk_max < top_val) {
                    // Valid Move: The max value in chunk is smaller than destination top.
                    // This maintains the sorted property (larger values below smaller values).
                    // We prioritize these moves heavily.
                    
                    // Base score for validity: 200,000
                    // Bonus for moving larger chunks (efficiency): sz * 1000
                    // Penalty for "waste" (gap between top_val and chunk_max): -(top_val - chunk_max)
                    // We prefer tight fits (small gap) and non-empty stacks over empty ones (if fit is good).
                    score = 200000LL + (long long)sz * 1000 - (top_val - chunk_max);
                } else {
                    // Invalid Move: We are placing a larger value on a smaller one.
                    // This blocks the smaller value, which is bad.
                    // If we must do this, we prefer to block larger values (less urgent).
                    // Score is proportional to top_val.
                    // Secondary priority: move larger chunks to save energy.
                    score = (long long)top_val * 1000 + sz;
                }

                if (score > best_score) {
                    best_score = score;
                    best_sz = sz;
                    best_dst = dst;
                }
            }
        }

        // Execute the best move found
        int move_start_idx = stacks[s_idx].size() - best_sz;
        int moved_box_v = stacks[s_idx][move_start_idx]; // This is the box 'v' for the operation
        
        ops.push_back({moved_box_v, best_dst});

        // Update the stack data structures
        vector<int> moving_chunk;
        moving_chunk.reserve(best_sz);
        // Collect boxes
        for (int k = 0; k < best_sz; ++k) {
            moving_chunk.push_back(stacks[s_idx][move_start_idx + k]);
        }
        // Remove from source stack
        stacks[s_idx].resize(move_start_idx);
        // Add to destination stack
        for (int x : moving_chunk) {
            stacks[best_dst].push_back(x);
        }
    }

    // Output the operations
    for (const auto& op : ops) {
        cout << op.v << " " << op.i << "\n";
    }

    return 0;
}