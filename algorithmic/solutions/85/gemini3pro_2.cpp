#include <iostream>
#include <vector>
#include <cstdlib>

using namespace std;

// Global variables to track state
int initialDeep;
int currentDeep;
int moves_count = 0;
// Safety thresholds to ensure we don't exceed the move limit while trying to optimize queries
const int MAX_MOVES = 100000;
const int SAFETY_THRESHOLD = 95000; 

// Function to query the current distance to the exit
int query_depth() {
    cout << "query" << endl;
    int d;
    if (!(cin >> d)) exit(0);
    return d;
}

// Function to move along an edge of color c
void move_to(int c) {
    cout << "move " << c << endl;
    int res;
    if (!(cin >> res)) exit(0);
    moves_count++;
    if (res == 1) {
        // Reached the exit
        exit(0);
    }
}

// History of correct moves taken to ascend
vector<int> history_moves;
// The color of the edge that leads back to the child node (downwards)
int last_down_edge = -1;

// Perform a single step upwards safely
// Cost: 1 query, 1-3 moves.
void safe_step() {
    // Identify the two candidate colors (excluding the one leading down)
    vector<int> candidates;
    for (int c = 0; c < 3; ++c) {
        if (c != last_down_edge) {
            candidates.push_back(c);
        }
    }
    
    // Pick the first candidate to try
    int try_c = candidates[0];
    move_to(try_c);
    
    // Check if we moved up or down
    int d = query_depth();
    if (d < currentDeep) {
        // Success: we moved up
        currentDeep = d;
        last_down_edge = try_c; // The edge we just traversed leads back down
        history_moves.push_back(try_c);
    } else {
        // Failure: we moved down
        move_to(try_c); // Move back to original node
        
        // The correct move must be the other candidate
        int other_c = candidates[1];
        move_to(other_c); 
        
        // We know this is correct without querying
        currentDeep--;
        last_down_edge = other_c;
        history_moves.push_back(other_c);
    }
}

// Initial step to determine orientation since last_down_edge is initially unknown
void initial_step() {
    // Try color 0
    move_to(0);
    int d = query_depth();
    if (d < currentDeep) {
        currentDeep = d;
        last_down_edge = 0;
        history_moves.push_back(0);
        return;
    }
    move_to(0); // Back
    
    // Try color 1
    move_to(1);
    d = query_depth();
    if (d < currentDeep) {
        currentDeep = d;
        last_down_edge = 1;
        history_moves.push_back(1);
        return;
    }
    move_to(1); // Back
    
    // Must be color 2
    move_to(2);
    currentDeep--;
    last_down_edge = 2;
    history_moves.push_back(2);
}

int main() {
    // Read initial depth
    if (!(cin >> initialDeep)) return 0;
    currentDeep = initialDeep;
    
    // If already at exit
    if (currentDeep == 0) return 0;
    
    // First move logic
    initial_step();
    
    // Loop until we reach the exit
    while (currentDeep > 0) {
        // If we are running low on allowed moves, stop batching optimization to ensure termination
        if (moves_count > SAFETY_THRESHOLD) {
            safe_step();
            continue;
        }
        
        // Pattern detection to save queries
        int best_period = -1;
        int H = history_moves.size();
        
        // Check for small periodic patterns in the move history
        // We check periods P from 1 to 20
        for (int P = 1; P <= 20 && P * 2 <= H; ++P) {
            bool match = true;
            // Check if the suffix of length P matches the preceding P moves
            for (int k = 0; k < P; ++k) {
                if (history_moves[H - P + k] != history_moves[H - 2 * P + k]) {
                    match = false;
                    break;
                }
            }
            if (match) {
                best_period = P;
                break; // Use the smallest period found
            }
        }
        
        if (best_period != -1) {
            // Pattern found, try to batch moves
            int batch_len = best_period;
            if (batch_len > currentDeep) batch_len = currentDeep;
            
            // Construct the predicted sequence of moves
            vector<int> seq;
            for (int k = 0; k < batch_len; ++k) {
                seq.push_back(history_moves[H - best_period + k]);
            }
            
            // Execute the batch
            for (int c : seq) {
                move_to(c);
            }
            
            // Verify with a single query
            int d = query_depth();
            
            if (d == currentDeep - batch_len) {
                // Prediction correct
                currentDeep = d;
                last_down_edge = seq.back();
                history_moves.insert(history_moves.end(), seq.begin(), seq.end());
            } else {
                // Prediction failed
                // Backtrack to the state before the batch
                for (int i = batch_len - 1; i >= 0; --i) {
                    move_to(seq[i]);
                }
                // Fallback to safe step
                safe_step();
            }
        } else {
            // No pattern detected, use safe step
            safe_step();
        }
    }
    
    return 0;
}