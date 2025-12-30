#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// A constant larger than any possible box value (N <= 200)
const int INF_VAL = 1000000;

void solve() {
    int N, M;
    if (!(cin >> N >> M)) return;

    // Stacks are 0-indexed internally.
    // stacks[i] is a vector where index 0 is the bottom-most box, back() is the top-most box.
    vector<vector<int>> stacks(M);
    for (int i = 0; i < M; ++i) {
        for (int j = 0; j < N / M; ++j) {
            int val;
            cin >> val;
            stacks[i].push_back(val);
        }
    }

    vector<pair<int, int>> operations;
    int current_target = 1;

    // Continue until all boxes from 1 to N are carried out
    while (current_target <= N) {
        // Find position of current_target
        int s_src = -1;
        int b_idx = -1;
        for (int i = 0; i < M; ++i) {
            for (int j = 0; j < stacks[i].size(); ++j) {
                if (stacks[i][j] == current_target) {
                    s_src = i;
                    b_idx = j;
                    break;
                }
            }
            if (s_src != -1) break;
        }

        // If target is at the top of its stack, remove it (Operation 2)
        if (b_idx == stacks[s_src].size() - 1) {
            operations.push_back({current_target, 0});
            stacks[s_src].pop_back();
            current_target++;
        } else {
            // Target is buried. We need to move boxes above it.
            // Boxes to move are from index b_idx+1 to top.
            // We use Operation 1 to move a chunk of boxes to another stack.
            // To minimize energy and avoid future blockages, we look for a "good" move.
            
            int current_top_idx = stacks[s_src].size() - 1;
            int limit = b_idx + 1;

            int best_p = -1;
            int best_dest = -1;

            // Strategy: Find the longest chunk from the top (starting at index p) 
            // that can be moved to another stack d such that top(d) > bottom(chunk).
            // Such a move is "stable" (larger value below smaller value).
            // We iterate p from 'limit' upwards. The first valid p gives the longest chunk.
            for (int p = limit; p <= current_top_idx; ++p) {
                int bottom_val = stacks[s_src][p];
                
                int best_d_for_p = -1;
                int min_diff = 2000000000;

                for (int d = 0; d < M; ++d) {
                    if (d == s_src) continue;
                    
                    int top_d = INF_VAL;
                    if (!stacks[d].empty()) {
                        top_d = stacks[d].back();
                    }

                    // Condition for a "good" placement
                    if (top_d > bottom_val) {
                        int diff = top_d - bottom_val;
                        // Prefer tighter fit to save larger gaps/empty stacks for later
                        if (diff < min_diff) {
                            min_diff = diff;
                            best_d_for_p = d;
                        }
                    }
                }

                if (best_d_for_p != -1) {
                    best_p = p;
                    best_dest = best_d_for_p;
                    break; // Found the longest valid chunk
                }
            }

            if (best_p != -1) {
                // Found a good move (Operation 1)
                int v = stacks[s_src][best_p];
                operations.push_back({v, best_dest + 1}); // Output is 1-based stack index

                // Execute move in memory
                vector<int> chunk;
                for (int k = best_p; k <= current_top_idx; ++k) {
                    chunk.push_back(stacks[s_src][k]);
                }
                stacks[s_src].resize(best_p);
                for (int x : chunk) {
                    stacks[best_dest].push_back(x);
                }
            } else {
                // No good move found (Filter 1 failed).
                // This implies for all possible chunks, and all destinations, top(dest) < bottom(chunk).
                // We are forced to make a "bad" move (creating an inversion).
                // We move only the single top box to minimize cost and structural impact.
                // We choose the destination with the largest top value to minimize the impact 
                // (placing on a large value blocks a box needed later rather than sooner).
                
                int v = stacks[s_src].back();
                int best_bad_d = -1;
                int max_val = -1;

                for (int d = 0; d < M; ++d) {
                    if (d == s_src) continue;
                    int val = 0;
                    if (!stacks[d].empty()) val = stacks[d].back();
                    
                    if (val > max_val) {
                        max_val = val;
                        best_bad_d = d;
                    }
                }

                // Execute move
                operations.push_back({v, best_bad_d + 1});
                stacks[s_src].pop_back();
                stacks[best_bad_d].push_back(v);
            }
        }
    }

    // Output all operations
    for (const auto& op : operations) {
        cout << op.first << " " << op.second << "\n";
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    solve();
    return 0;
}