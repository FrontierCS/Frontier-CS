#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>

using namespace std;

// Global state tracking
int current_deep;
int moves_count = 0;
const int MAX_MOVES = 100000;

// Terminates the program
void die() {
    exit(0);
}

// Performs a move operation
// c: color to move (0, 1, 2)
// Returns result from interactor (always 0 if not exit, because 1 exits)
int make_move(int c) {
    if (moves_count >= MAX_MOVES) die();
    cout << "move " << c << endl;
    moves_count++;
    int res;
    if (!(cin >> res)) die();
    if (res == 1) die();
    return res;
}

// Performs a query operation
// Returns current depth
int query_dist() {
    cout << "query" << endl;
    int d;
    if (!(cin >> d)) die();
    return d;
}

// Predicts the next sequence of moves based on history
vector<int> predict_pattern(const vector<int>& history, int max_len) {
    int n = history.size();
    if (n < 4) return {}; 
    
    // Check for small periods
    for (int p = 1; p <= 20 && p * 2 <= n; ++p) {
        bool ok = true;
        int checks = 0;
        // Verify the period matches the end of history
        // Check last 3*p elements or as many as available
        for (int k = 1; k <= 3 * p && n - k - p >= 0; ++k) {
             if (history[n - k] != history[n - k - p]) {
                 ok = false;
                 break;
             }
             checks++;
        }
        
        // Heuristic: require at least 2 full periods or sufficient coverage
        if (ok && checks >= 2 * p) {
            vector<int> seq;
            for (int i = 0; i < max_len; ++i) {
                seq.push_back(history[n - p + (i % p)]);
            }
            return seq;
        }
    }
    return {};
}

int main() {
    // Optimize I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    int initial_deep;
    if (!(cin >> initial_deep)) return 0;
    if (initial_deep == 0) return 0;
    
    current_deep = initial_deep;
    vector<int> history;
    int last_up_color = -1; 
    
    int consecutive_success = 0;

    while (current_deep > 0) {
        int remaining_moves = MAX_MOVES - moves_count;
        // Safety margin: ensure we can single-step the rest of the way if needed
        // Worst case single step cost is 3 moves per level (1 down, 1 back, 1 up)
        int reserved = 3 * current_deep + 200;
        
        // Attempt batch move if confident and have spare moves
        if (remaining_moves > reserved && consecutive_success > 2) {
             int plan_len = 1 << (consecutive_success - 2);
             if (plan_len > 200) plan_len = 200; // Cap batch size
             if (plan_len > current_deep) plan_len = current_deep;
             
             // Cost of failure is 2 * plan_len moves (do and undo)
             if (remaining_moves - reserved > 2 * plan_len) {
                 vector<int> prediction = predict_pattern(history, plan_len);
                 if (!prediction.empty()) {
                     // Execute batch
                     for (int c : prediction) {
                         make_move(c);
                     }
                     
                     int d = query_dist();
                     if (d == current_deep - (int)prediction.size()) {
                         // Batch Success
                         current_deep = d;
                         for (int c : prediction) history.push_back(c);
                         last_up_color = prediction.back();
                         consecutive_success++;
                         continue; 
                     } else {
                         // Batch Fail: Backtrack
                         // To backtrack, we perform the moves in reverse order
                         vector<int> rev = prediction;
                         reverse(rev.begin(), rev.end());
                         for (int c : rev) {
                             make_move(c);
                         }
                         consecutive_success = 0;
                         // Fall through to single step
                     }
                 }
             }
        }
        
        // Single Step Strategy
        vector<int> candidates;
        for(int c=0; c<3; ++c) {
            if (c != last_up_color) candidates.push_back(c);
        }
        
        // Sort candidates based on prediction
        vector<int> next_one = predict_pattern(history, 1);
        if (!next_one.empty()) {
            for (size_t i=0; i<candidates.size(); ++i) {
                if (candidates[i] == next_one[0]) {
                    swap(candidates[0], candidates[i]);
                    break;
                }
            }
        }
        
        bool step_success = false;
        // Try candidates
        // We iterate up to size-1, if all fail, the last one is the correct path
        for (size_t i = 0; i < candidates.size() - 1; ++i) {
            int c = candidates[i];
            make_move(c);
            int d = query_dist();
            if (d < current_deep) {
                current_deep = d;
                history.push_back(c);
                last_up_color = c;
                step_success = true;
                consecutive_success++;
                break;
            } else {
                // Failed (went deeper), go back
                make_move(c);
            }
        }
        
        if (!step_success) {
            // Elimination logic: must be the last candidate
            int c = candidates.back();
            make_move(c);
            // Assume success without query to save queries
            current_deep--;
            history.push_back(c);
            last_up_color = c;
            consecutive_success = 0;
        }
    }
    
    return 0;
}