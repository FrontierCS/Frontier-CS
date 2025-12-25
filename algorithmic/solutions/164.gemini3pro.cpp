#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Constants for tuning heuristics
// Energy cost for a move is (k+1).
// Heuristic weights should be balanced against this cost.
const double WEIGHT_INVERSION = 1000.0;   // High penalty for placing larger value on smaller
const double WEIGHT_BURY = 50.0;          // Penalty for adding height above soon-needed boxes
const double WEIGHT_EMPTY = 400.0;        // Penalty for consuming an empty stack
const double BONUS_GOOD_ORDER = 100.0;    // Bonus (negative penalty) for placing smaller on larger

int N, M;
vector<vector<int>> stacks;

struct Move {
    int v, i;
};

// Helper to find a box's location
struct Pos {
    int s, h; // stack index (1-based), height index (0-based)
};

Pos find_box(int v) {
    for (int i = 1; i <= M; ++i) {
        for (int j = 0; j < stacks[i].size(); ++j) {
            if (stacks[i][j] == v) return {i, j};
        }
    }
    return {-1, -1};
}

int main() {
    // Optimize I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M)) return 0;

    stacks.resize(M + 1);
    for (int i = 1; i <= M; ++i) {
        for (int j = 0; j < N / M; ++j) {
            int val;
            cin >> val;
            stacks[i].push_back(val);
        }
    }

    vector<Move> ops;
    int cur_target = 1;

    // Main loop to remove boxes 1 to N
    while (cur_target <= N) {
        Pos p = find_box(cur_target);
        int s_idx = p.s;
        int h_idx = p.h; // index of target in stack

        // If target is at the top (end of vector)
        if (h_idx == stacks[s_idx].size() - 1) {
            // Operation 2: Carry out
            ops.push_back({cur_target, 0});
            stacks[s_idx].pop_back();
            cur_target++;
        } else {
            // Target is buried. We need to move boxes above it.
            // Boxes above are at indices [h_idx + 1, ..., stacks[s_idx].size()-1].
            // We can choose to move a sub-stack starting from any index 'split' > h_idx.
            
            double best_score = 1e18; // Minimize score
            int best_split = -1;
            int best_dst = -1;

            int stack_top_idx = stacks[s_idx].size() - 1;
            
            // Iterate over all valid split points
            for (int split = h_idx + 1; split <= stack_top_idx; ++split) {
                int chunk_size = stack_top_idx - split + 1;
                int chunk_bottom_val = stacks[s_idx][split];
                
                // Try all valid destination stacks
                for (int dst = 1; dst <= M; ++dst) {
                    if (dst == s_idx) continue;
                    
                    double current_score = 0;
                    
                    // 1. Immediate Energy Cost: size + 1
                    current_score += (chunk_size + 1);
                    
                    // Check destination state
                    bool dst_empty = stacks[dst].empty();
                    int dst_top_val = dst_empty ? (N + 1) : stacks[dst].back();
                    
                    // 2. Penalty for Inversion
                    // Bad: Placing a larger value on a smaller value (blocks the smaller one).
                    if (chunk_bottom_val > dst_top_val) {
                        current_score += WEIGHT_INVERSION;
                    } else {
                        // Good: Placing smaller on larger (or on empty), maintains access order.
                        current_score -= BONUS_GOOD_ORDER;
                    }
                    
                    // 3. Penalty for using empty stack
                    // Prefer keeping empty stacks as buffers unless necessary.
                    if (dst_empty) {
                        current_score += WEIGHT_EMPTY;
                    }
                    
                    // 4. Penalty for burying vital boxes
                    // If we place boxes on top of values needed soon, we incur future costs.
                    if (!dst_empty) {
                        double burying_penalty = 0;
                        for (int val : stacks[dst]) {
                            // All values in stacks are > cur_target (since <= cur_target are removed/current)
                            int dist = val - cur_target;
                            // Consider boxes needed in the near future
                            if (dist < 40) { 
                                double urgency = 1.0 / (double)(dist + 1);
                                burying_penalty += urgency;
                            }
                        }
                        current_score += chunk_size * WEIGHT_BURY * burying_penalty;
                    }
                    
                    if (current_score < best_score) {
                        best_score = current_score;
                        best_split = split;
                        best_dst = dst;
                    }
                }
            }
            
            // Execute the best move
            int move_box_val = stacks[s_idx][best_split];
            ops.push_back({move_box_val, best_dst});
            
            // Update data structures
            vector<int> chunk;
            chunk.insert(chunk.end(), stacks[s_idx].begin() + best_split, stacks[s_idx].end());
            stacks[s_idx].erase(stacks[s_idx].begin() + best_split, stacks[s_idx].end());
            
            stacks[best_dst].insert(stacks[best_dst].end(), chunk.begin(), chunk.end());
        }
    }

    // Output results
    for (auto &op : ops) {
        cout << op.v << " " << op.i << "\n";
    }

    return 0;
}