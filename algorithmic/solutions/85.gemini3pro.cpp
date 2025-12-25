#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cstdlib>

using namespace std;

// Global variables for problem state
int initialDeep;
int currentDeep;
int moveCount = 0;
const int MAX_MOVES = 100000;

// Function to query the distance from the exit
// Flushes output and reads response
int query_dist() {
    cout << "query" << endl;
    int d;
    if (!(cin >> d)) exit(0);
    return d;
}

// Function to move to a neighbor node
// Checks for exit condition
void move_step(int c) {
    if (moveCount >= MAX_MOVES) return;
    cout << "move " << c << endl;
    moveCount++;
    int res;
    if (!(cin >> res)) exit(0);
    if (res == 1) exit(0); // Reached exit
}

// State tracking
int last_in_color = -1; // The color of the edge we arrived from (downwards)
vector<int> offset_history; // History of relative moves (1 or 2)

// Predict next offsets based on history pattern
vector<int> predict_offsets(int limit) {
    vector<int> prediction;
    if (offset_history.empty()) return prediction;
    
    int n = offset_history.size();
    int best_period = -1;
    // Check for short periods (patterns) in history
    int check_limit = 20;
    int suffix_len = min(n, 60); 
    
    for (int p = 1; p <= check_limit; ++p) {
        if (n < p) continue;
        bool ok = true;
        int matches = 0;
        for (int i = 0; i < suffix_len; ++i) {
            int idx = n - 1 - i;
            if (idx - p >= 0) {
                if (offset_history[idx] != offset_history[idx - p]) {
                    ok = false;
                    break;
                }
                matches++;
            }
        }
        if (ok && matches > 0) {
            best_period = p;
            break; 
        }
    }
    
    if (best_period != -1) {
        for(int k=0; k<limit; k++) {
            prediction.push_back(offset_history[n - best_period + (k % best_period)]);
        }
    }
    return prediction;
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> initialDeep)) return 0;
    currentDeep = initialDeep;
    
    // Initial blind search to find the first step up and establish last_in_color
    if (currentDeep > 0) {
        move_step(0);
        int d = query_dist();
        if (d < currentDeep) {
            currentDeep = d;
            last_in_color = 0;
        } else {
            move_step(0); // move back
            move_step(1);
            d = query_dist();
            if (d < currentDeep) {
                currentDeep = d;
                last_in_color = 1;
            } else {
                move_step(1); // move back
                move_step(2);
                // Must be correct direction
                currentDeep--;
                last_in_color = 2;
            }
        }
    }
    
    int batch_size = 1;
    
    while (currentDeep > 0) {
        // Attempt to predict a sequence of moves to save queries
        vector<int> predicted_offsets;
        if (offset_history.size() >= 4) {
             predicted_offsets = predict_offsets(batch_size);
        }
        
        bool batch_success = false;
        if (!predicted_offsets.empty()) {
            vector<int> moves_made;
            int temp_last = last_in_color;
            int steps_planned = 0;
            
            // Execute batch
            for (int off : predicted_offsets) {
                if (currentDeep - (int)moves_made.size() <= 0) break;
                int next_c = (temp_last + off) % 3;
                move_step(next_c);
                moves_made.push_back(next_c);
                temp_last = next_c;
                steps_planned++;
            }
            
            if (steps_planned > 0) {
                // Validate batch with a single query
                int d = query_dist();
                if (d == currentDeep - steps_planned) {
                    currentDeep = d;
                    last_in_color = temp_last;
                    for (int i = 0; i < steps_planned; ++i) {
                         offset_history.push_back(predicted_offsets[i]);
                    }
                    // Adaptively increase batch size on success
                    if (batch_size < currentDeep && batch_size < 500) {
                         batch_size *= 2;
                    }
                    batch_success = true;
                } else {
                    // Prediction failed, backtrack to start of batch
                    for (int i = moves_made.size() - 1; i >= 0; --i) {
                        move_step(moves_made[i]);
                    }
                    // Reset batch size on failure
                    batch_size = 1;
                }
            }
        }
        
        if (batch_success) continue;
        
        // Fallback: Step-by-step exploration
        // Given last_in_color (from child), parent is at (last_in+1)%3 or (last_in+2)%3
        int c1 = (last_in_color + 1) % 3;
        int c2 = (last_in_color + 2) % 3;
        
        move_step(c1);
        int d = query_dist();
        if (d < currentDeep) {
            currentDeep = d;
            last_in_color = c1;
            offset_history.push_back(1);
        } else {
            move_step(c1); // back
            move_step(c2); // must be the other one
            // We can infer success without querying to save queries
            currentDeep--;
            last_in_color = c2;
            offset_history.push_back(2);
        }
    }

    return 0;
}