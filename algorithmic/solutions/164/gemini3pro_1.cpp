#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Global variables to store problem state
int N, M;
vector<vector<int>> stacks;
struct Op {
    int v, i;
};
vector<Op> result;

// Helper function: Find the stack index and position within stack for a given box
pair<int, int> find_box(int v) {
    for (int i = 0; i < M; ++i) {
        for (int j = 0; j < (int)stacks[i].size(); ++j) {
            if (stacks[i][j] == v) {
                return {i, j};
            }
        }
    }
    return {-1, -1};
}

// Execute Operation 1: Move box v and all boxes above it to dest_idx
void op1(int v, int dest_idx) {
    // Record operation (1-based index for destination)
    result.push_back({v, dest_idx + 1});
    
    pair<int, int> loc = find_box(v);
    int src_idx = loc.first;
    int pos = loc.second;
    
    // Identify the sequence of boxes to move
    vector<int> moving;
    for (int k = pos; k < (int)stacks[src_idx].size(); ++k) {
        moving.push_back(stacks[src_idx][k]);
    }
    
    // Remove from source stack
    stacks[src_idx].resize(pos);
    
    // Append to destination stack
    for (int x : moving) {
        stacks[dest_idx].push_back(x);
    }
}

// Execute Operation 2: Remove box v from the warehouse
void op2(int v) {
    // Record operation (0 indicates removal)
    result.push_back({v, 0});
    pair<int, int> loc = find_box(v);
    int src_idx = loc.first;
    // Box v should be at the top
    stacks[src_idx].pop_back();
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M)) return 0;

    stacks.resize(M);
    for (int i = 0; i < M; ++i) {
        for (int j = 0; j < N / M; ++j) {
            int val;
            cin >> val;
            stacks[i].push_back(val);
        }
    }

    // Iterate through targets 1 to N
    for (int target = 1; target <= N; ++target) {
        while (true) {
            pair<int, int> loc = find_box(target);
            int s_idx = loc.first;
            int pos = loc.second;
            
            // If target is at the top of its stack, we can remove it
            if (pos == (int)stacks[s_idx].size() - 1) {
                op2(target);
                break;
            }
            
            // Target is buried. We must move boxes above it to other stacks.
            // Strategy: Peel off the top-most "monotonic decreasing" chunk.
            // A chunk is "monotonic decreasing" if values decrease from bottom to top.
            // This represents a "good" stack segment (larger value supports smaller value).
            // We split at "bad" transitions (smaller value supports larger value) to fix sorting.
            
            int top_idx = (int)stacks[s_idx].size() - 1;
            int start_chunk = top_idx;
            
            // Extend chunk downwards as long as the order is "good"
            while (start_chunk > pos + 1) {
                if (stacks[s_idx][start_chunk - 1] > stacks[s_idx][start_chunk]) {
                    start_chunk--;
                } else {
                    break;
                }
            }
            
            int box_to_move = stacks[s_idx][start_chunk];
            
            // Choose the best destination stack for this chunk
            int best_dest = -1;
            int min_diff = 2000; // Initialize with a large value
            
            int best_dest_bad = -1;
            int max_top_bad = -1;
            
            for (int i = 0; i < M; ++i) {
                if (i == s_idx) continue;
                
                // Effective top of stack i. Empty stack acts as top = infinity (1000).
                int t_val = stacks[i].empty() ? 1000 : stacks[i].back();
                
                if (t_val > box_to_move) {
                    // Class A: Good placement (New top > Moving box).
                    // We prefer the smallest t_val that is > box_to_move ("Tight Fit").
                    // This preserves stacks with very large tops for larger boxes later.
                    if (t_val - box_to_move < min_diff) {
                        min_diff = t_val - box_to_move;
                        best_dest = i;
                    }
                } else {
                    // Class B: Bad placement (New top < Moving box). Creates inversion.
                    // We prefer the largest t_val to minimize the damage (burying a larger value is better than burying a small one).
                    if (t_val > max_top_bad) {
                        max_top_bad = t_val;
                        best_dest_bad = i;
                    }
                }
            }
            
            int final_dest = best_dest;
            // If no Class A destination exists, forced to use Class B
            if (final_dest == -1) {
                final_dest = best_dest_bad;
            }
            
            // Perform the move
            op1(box_to_move, final_dest);
        }
    }

    // Output the sequence of operations
    for (const auto& op : result) {
        cout << op.v << " " << op.i << "\n";
    }

    return 0;
}