#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>

using namespace std;

struct Point {
    int r, c;
};

// Global variables to store the state
int grid_vals[30][30];
Point pos[465]; // pos[v] stores current position of value v
int target_row_map[465]; // Maps value v to its target row (layered solution)
vector<int> row_start_val(31);
vector<int> row_end_val(31); // Exclusive end for values in a row

struct Move {
    int r1, c1, r2, c2;
};
vector<Move> moves_history;

// Perform a swap between two adjacent cells and record it
void perform_swap(Point p1, Point p2) {
    int v1 = grid_vals[p1.r][p1.c];
    int v2 = grid_vals[p2.r][p2.c];
    
    swap(grid_vals[p1.r][p1.c], grid_vals[p2.r][p2.c]);
    pos[v1] = p2;
    pos[v2] = p1;
    
    moves_history.push_back({p1.r, p1.c, p2.r, p2.c});
}

// Calculate distance in the pyramid grid graph
int dist(Point p1, Point p2) {
    int r1 = p1.r, c1 = p1.c;
    int r2 = p2.r, c2 = p2.c;
    // Ensure r1 <= r2 for calculation
    if (r1 > r2) {
        swap(r1, r2);
        swap(c1, c2);
    }
    int dr = r2 - r1;
    int dc = c2 - c1;
    
    // Distance logic derived from grid connectivity
    if (dc < 0) return dr - dc;
    if (dc <= dr) return dr;
    return dc;
}

int main() {
    // Fast IO
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int N = 30;
    
    // Input
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j <= i; ++j) {
            cin >> grid_vals[i][j];
            pos[grid_vals[i][j]] = {i, j};
        }
    }

    // Precompute target rows for each value based on sorted order
    // Values 0..0 -> Row 0
    // Values 1..2 -> Row 1
    // Values 3..5 -> Row 2
    // etc.
    int v = 0;
    for (int i = 0; i < N; ++i) {
        row_start_val[i] = v;
        for (int j = 0; j <= i; ++j) {
            target_row_map[v] = i;
            v++;
        }
        row_end_val[i] = v;
    }
    
    // Algorithm:
    // Process rows from 0 to N-2.
    // For each row i, identify balls that belong to row i but are currently at row > i.
    // Identify slots in row i that currently hold balls belonging to row > i.
    // Match them greedily (closest pair) and move the correct balls up.
    
    for (int i = 0; i < N - 1; ++i) {
        // Identify empty slots in current row
        // A slot is effectively "empty" if it contains a value meant for a deeper row.
        vector<Point> empty_slots;
        for (int j = 0; j <= i; ++j) {
            int val = grid_vals[i][j];
            if (target_row_map[val] > i) {
                empty_slots.push_back({i, j});
            }
        }
        
        if (empty_slots.empty()) continue;

        // Identify candidates: balls belonging to row i, currently in rows > i
        vector<int> candidates;
        for (int val = row_start_val[i]; val < row_end_val[i]; ++val) {
            if (pos[val].r > i) {
                candidates.push_back(val);
            }
        }
        
        // Greedily fill slots
        while (!empty_slots.empty()) {
            if (candidates.empty()) break; // Should not happen if logic is correct
            
            int best_cand_idx = -1;
            int best_slot_idx = -1;
            int min_d = 1000000;
            
            // Find closest candidate-slot pair
            for (int s_idx = 0; s_idx < empty_slots.size(); ++s_idx) {
                for (int c_idx = 0; c_idx < candidates.size(); ++c_idx) {
                    int val = candidates[c_idx];
                    int d = dist(pos[val], empty_slots[s_idx]);
                    if (d < min_d) {
                        min_d = d;
                        best_cand_idx = c_idx;
                        best_slot_idx = s_idx;
                    }
                }
            }
            
            int val = candidates[best_cand_idx];
            Point target = empty_slots[best_slot_idx];
            
            // Move the chosen ball to the target slot
            while (pos[val].r != target.r || pos[val].c != target.c) {
                Point curr = pos[val];
                Point best_next = curr;
                int best_step_dist = 1000000;
                
                // Try moving to neighbors
                // Since target is at row i and curr at > i, we generally move Up or Sideways
                vector<Point> nexts;
                // Up-Left: (r-1, c-1)
                if (curr.r > 0 && curr.c > 0) nexts.push_back({curr.r - 1, curr.c - 1});
                // Up-Right: (r-1, c)
                if (curr.r > 0 && curr.c <= curr.r - 1) nexts.push_back({curr.r - 1, curr.c});
                // Left: (r, c-1)
                if (curr.c > 0) nexts.push_back({curr.r, curr.c - 1});
                // Right: (r, c+1)
                if (curr.c < curr.r) nexts.push_back({curr.r, curr.c + 1});
                
                // Pick neighbor that is closest to target
                for (auto np : nexts) {
                    int d = dist(np, target);
                    if (d < best_step_dist) {
                        best_step_dist = d;
                        best_next = np;
                    }
                }
                
                perform_swap(curr, best_next);
                if (moves_history.size() >= 10000) break;
            }
            if (moves_history.size() >= 10000) break;
            
            // Remove matched pair
            candidates.erase(candidates.begin() + best_cand_idx);
            empty_slots.erase(empty_slots.begin() + best_slot_idx);
        }
        if (moves_history.size() >= 10000) break;
    }

    // Output results
    cout << moves_history.size() << "\n";
    for (const auto& m : moves_history) {
        cout << m.r1 << " " << m.c1 << " " << m.r2 << " " << m.c2 << "\n";
    }

    return 0;
}