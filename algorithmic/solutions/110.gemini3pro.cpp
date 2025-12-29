#include <iostream>
#include <vector>
#include <random>
#include <chrono>
#include <cstring>
#include <algorithm>

using namespace std;

// Using GCC extension for 128-bit integers to represent the 8x14 (112 cells) grid mask
typedef unsigned __int128 u128;

const int ROWS = 8;
const int COLS = 14;
const int MAX_X = 50000; // Search limit
const int LOOKAHEAD = 50; // Secondary metric lookahead

u128 pos_masks[10];
u128 masks[MAX_X + LOOKAHEAD + 100];
u128 COL0_MASK = 0;
u128 COL13_MASK = 0;

int grid[ROWS][COLS];

// Initialize column masks for bitwise operations
void init_masks() {
    COL0_MASK = 0;
    COL13_MASK = 0;
    for (int r = 0; r < ROWS; ++r) {
        COL0_MASK |= ((u128)1 << (r * COLS + 0));
        COL13_MASK |= ((u128)1 << (r * COLS + 13));
    }
}

// Expand the set of positions to all adjacent cells (8 directions)
inline u128 expand(u128 m) {
    if (m == 0) return 0;
    u128 m_noL = m & ~COL0_MASK;
    u128 m_noR = m & ~COL13_MASK;
    
    u128 res = (m_noL >> 1) | (m_noR << 1); // Left, Right
    res |= (m >> 14) | (m << 14); // Up, Down
    res |= (m_noL >> 15) | (m_noR >> 13); // Up-Left, Up-Right
    res |= (m_noL << 13) | (m_noR << 15); // Down-Left, Down-Right
    return res;
}

// Evaluate the grid. Returns {primary_score, secondary_score}
// Primary: The largest X such that 1..X are readable.
// Secondary: How many numbers in [X+2, X+1+LOOKAHEAD] are readable.
pair<int, int> evaluate() {
    int first_missing = -1;
    int secondary = 0;
    int limit = MAX_X;
    
    // Check single digit numbers 1..9
    for (int k = 1; k <= 9; ++k) {
        masks[k] = pos_masks[k];
        if (masks[k] == 0) {
            if (first_missing == -1) first_missing = k;
        }
        if (first_missing != -1) {
            if (masks[k] != 0) secondary++;
            if (k > first_missing + LOOKAHEAD) return {first_missing - 1, secondary};
        }
    }
    
    // Check numbers >= 10
    for (int k = 10; k < limit; ++k) {
        // Optimization: if prefix is missing, number is missing
        if (masks[k/10] == 0) {
            masks[k] = 0;
        } else {
            masks[k] = expand(masks[k/10]) & pos_masks[k%10];
        }
        
        if (masks[k] == 0) {
            if (first_missing == -1) first_missing = k;
        }
        
        if (first_missing != -1) {
            if (masks[k] != 0) secondary++;
            if (k > first_missing + LOOKAHEAD) return {first_missing - 1, secondary};
        }
    }
    
    if (first_missing == -1) return {limit, 0};
    return {first_missing - 1, secondary};
}

int main() {
    init_masks();
    
    // Setup random number generator
    // Using time-based seed for exploration
    auto seed = chrono::steady_clock::now().time_since_epoch().count();
    mt19937 rng(seed);
    
    // Initialize grid randomly
    for (int r = 0; r < ROWS; ++r) {
        for (int c = 0; c < COLS; ++c) {
            grid[r][c] = rng() % 10;
        }
    }
    
    // Initial mask build
    for (int d=0; d<10; ++d) pos_masks[d] = 0;
    for (int r=0; r<ROWS; ++r) {
        for (int c=0; c<COLS; ++c) {
            pos_masks[grid[r][c]] |= ((u128)1 << (r * COLS + c));
        }
    }
    
    pair<int, int> current_score = evaluate();
    pair<int, int> best_global_score = current_score;
    int best_grid[ROWS][COLS];
    memcpy(best_grid, grid, sizeof(grid));
    
    auto start_time = chrono::steady_clock::now();
    long long iterations = 0;
    
    // Optimization loop (Hill Climbing with lookahead tie-breaking)
    while (true) {
        iterations++;
        // Check time limit every 1024 iterations
        if ((iterations & 1023) == 0) {
            auto curr_time = chrono::steady_clock::now();
            auto diff = chrono::duration_cast<chrono::milliseconds>(curr_time - start_time).count();
            if (diff > 58500) break; // Stop a bit before 60s
        }
        
        // Mutate a random cell
        int r = rng() % ROWS;
        int c = rng() % COLS;
        int old_val = grid[r][c];
        int new_val = rng() % 10;
        
        if (old_val == new_val) {
            new_val = (new_val + 1) % 10;
        }
        
        // Apply change
        grid[r][c] = new_val;
        u128 bit = ((u128)1 << (r * COLS + c));
        pos_masks[old_val] ^= bit; // Remove old (XOR safe as we know it was set)
        pos_masks[new_val] |= bit; // Add new
        
        pair<int, int> new_score = evaluate();
        
        bool accept = false;
        
        // Acceptance criteria
        if (new_score.first > current_score.first) {
            accept = true;
        } else if (new_score.first == current_score.first) {
            // If primary score is equal, check secondary
            if (new_score.second >= current_score.second) {
                accept = true;
            }
        }
        
        if (accept) {
            current_score = new_score;
            if (current_score.first > best_global_score.first || 
               (current_score.first == best_global_score.first && current_score.second > best_global_score.second)) {
                best_global_score = current_score;
                memcpy(best_grid, grid, sizeof(grid));
            }
        } else {
            // Revert change
            grid[r][c] = old_val;
            pos_masks[old_val] |= bit;
            pos_masks[new_val] ^= bit;
        }
    }
    
    // Output the best grid found
    for (int r = 0; r < ROWS; ++r) {
        for (int c = 0; c < COLS; ++c) {
            cout << best_grid[r][c];
        }
        cout << endl;
    }
    
    return 0;
}