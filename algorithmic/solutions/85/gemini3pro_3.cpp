#include <iostream>
#include <vector>
#include <algorithm>
#include <cstdlib>

using namespace std;

// Model to predict the parent direction based on incoming color
// model_next[incoming_color] = outgoing_to_parent_color
int model_next[3] = {-1, -1, -1};
int consecutive_hits = 0;

// Function to check interactor response after a move
// If response is 1, we reached the exit.
void check_response(int r) {
    if (r == 1) exit(0);
}

// Perform query operation
int query_dist() {
    cout << "query" << endl;
    int d;
    cin >> d;
    return d;
}

// Perform move operation
void move_op(int c) {
    cout << "move " << c << endl;
    int r;
    cin >> r;
    check_response(r);
}

int main() {
    // Optimize IO operations
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int initialDeep;
    if (!(cin >> initialDeep)) return 0;
    // If we are already at exit (distance 0), though problem implies initialDeep > 0
    if (initialDeep == 0) return 0;

    int currentDeep = initialDeep;
    int last_in = -1; // Color of the edge we just traversed to arrive here
    int skip_budget = 0; // Number of queries we can skip

    while (true) {
        // Determine candidate moves (edges other than the one we came from)
        vector<int> cands;
        if (last_in == -1) {
            cands = {0, 1, 2};
        } else {
            for (int i = 0; i < 3; ++i) {
                if (i != last_in) cands.push_back(i);
            }
        }

        int best_move = -1;
        // Use model prediction if available
        if (last_in != -1 && model_next[last_in] != -1) {
            int pred = model_next[last_in];
            // Verify prediction is a valid candidate
            bool ok = false;
            for (int x : cands) if (x == pred) ok = true;
            if (ok) best_move = pred;
        }

        // If no prediction or invalid, pick the first candidate
        if (best_move == -1) {
            best_move = cands[0];
        }

        // Strategy: Skip queries if we are confident (skip_budget > 0)
        if (skip_budget > 0) {
            move_op(best_move);
            // Assume success
            last_in = best_move;
            currentDeep--;
            skip_budget--;
            continue;
        }

        // Uncertain mode: move and verify with query
        move_op(best_move);
        int d = query_dist();

        if (d < currentDeep) {
            // Success: we moved up closer to exit
            if (last_in != -1) {
                if (model_next[last_in] == best_move) {
                    consecutive_hits++;
                } else {
                    // Update model with new observation
                    model_next[last_in] = best_move;
                    consecutive_hits = 0;
                }
            }
            
            currentDeep = d;
            last_in = best_move;

            // Increase confidence to skip future queries
            // We use min to cap the skip length to avoid drifting too far if pattern breaks
            if (consecutive_hits >= 5) {
                skip_budget = min(consecutive_hits, 20); 
            }
        } else {
            // Failure: we moved down (away from exit)
            consecutive_hits = 0;
            
            // Backtrack to previous node
            move_op(best_move);
            // Current depth is back to `currentDeep` (which is `d - 1` effectively)
            
            // Try alternatives
            if (last_in != -1) {
                // Only one alternative remaining since degree is 3
                int other = -1;
                for (int x : cands) if (x != best_move) other = x;
                
                move_op(other);
                // By elimination, this must be the parent
                model_next[last_in] = other;
                last_in = other;
                
                // Depth logic: we were at H, went down to H+1 (d), back to H, then up to H-1.
                // So new depth is d - 2.
                currentDeep = d - 2; 
                
                // We restart confidence
                consecutive_hits = 1; 
            } else {
                // Start case (last_in == -1): we tried best_move and failed.
                // Try next candidate.
                int first_fail = best_move;
                int second_try = -1;
                for (int x : cands) if (x != first_fail) { second_try = x; break; }
                
                move_op(second_try);
                int d2 = query_dist();
                if (d2 < currentDeep) {
                     // Success
                     currentDeep = d2;
                     last_in = second_try;
                } else {
                    // Second try failed too
                    move_op(second_try); // Back
                    // Third candidate must be correct
                    int third_try = -1;
                    for (int x : cands) if (x != first_fail && x != second_try) third_try = x;
                    
                    move_op(third_try);
                    last_in = third_try;
                    // d2 was currentDeep + 1. So we went down, back, down, back, up.
                    // Correct depth is d2 - 2.
                    currentDeep = d2 - 2;
                }
            }
        }
    }
    return 0;
}