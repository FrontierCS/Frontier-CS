#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <random>
#include <chrono>

using namespace std;

const int H = 8;
const int W = 14;

// The grid is a global variable to be modified by the search algorithm.
vector<vector<int>> grid(H, vector<int>(W));

/**
 * @brief Checks if a given integer n can be "read" from the grid.
 *
 * A number is readable if its digit sequence corresponds to a path of
 * adjacent cells (including diagonals) in the grid.
 *
 * This function uses a BFS-like approach. It maintains a queue of all
 * possible positions for the current step of the path.
 *
 * @param n The integer to check.
 * @return True if the number is readable, false otherwise.
 */
bool is_readable(int n) {
    string s = to_string(n);
    int len = s.length();
    
    vector<pair<int, int>> q;
    
    int first_digit = s[0] - '0';
    for (int r = 0; r < H; ++r) {
        for (int c = 0; c < W; ++c) {
            if (grid[r][c] == first_digit) {
                q.push_back({r, c});
            }
        }
    }

    if (q.empty()) return false;
    
    vector<vector<bool>> visited_next(H, vector<bool>(W));

    for (int i = 1; i < len; ++i) {
        if (q.empty()) return false;
        
        int current_digit = s[i] - '0';
        vector<pair<int, int>> next_q;
        fill(visited_next.begin(), visited_next.end(), vector<bool>(W, false));

        for (auto const& pos : q) {
            int pr = pos.first;
            int pc = pos.second;
            
            for (int dr = -1; dr <= 1; ++dr) {
                for (int dc = -1; dc <= 1; ++dc) {
                    if (dr == 0 && dc == 0) continue;
                    int nr = pr + dr;
                    int nc = pc + dc;

                    if (nr >= 0 && nr < H && nc >= 0 && nc < W) {
                        if (grid[nr][nc] == current_digit && !visited_next[nr][nc]) {
                            next_q.push_back({nr, nc});
                            visited_next[nr][nc] = true;
                        }
                    }
                }
            }
        }
        q = next_q;
    }
    
    return !q.empty();
}

/**
 * @brief Calculates the score of the current global grid.
 *
 * The score is the largest integer X such that all integers from 1 to X
 * are readable. It checks integers 1, 2, 3, ... sequentially until one
 * is found to be not readable.
 *
 * @return The score of the grid.
 */
int calculate_score() {
    for (int k = 1; ; ++k) {
        if (!is_readable(k)) {
            return k - 1;
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    auto start_time = chrono::high_resolution_clock::now();

    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_int_distribution<int> dist_row(0, H - 1);
    uniform_int_distribution<int> dist_col(0, W - 1);
    uniform_int_distribution<int> dist_digit(0, 9);
    uniform_real_distribution<double> dist_prob(0.0, 1.0);

    // Initialize with the sample grid, which is a good starting point.
    grid = {
        {1,0,2,0,3,3,4,4,5,3,6,4,7,3},
        {0,1,0,2,0,1,0,2,0,1,0,2,0,1},
        {0,0,0,0,0,0,0,0,0,0,8,3,9,0},
        {0,0,0,0,0,0,0,0,0,0,0,4,0,0},
        {0,0,0,0,0,0,0,0,0,0,0,0,0,0},
        {5,5,6,0,0,0,0,0,0,0,0,0,8,9},
        {7,8,9,0,0,0,6,6,0,0,0,0,8,9},
        {0,0,0,0,0,7,8,9,0,0,0,0,7,7}
    };
    
    int current_score = calculate_score();
    vector<vector<int>> best_grid = grid;
    int best_score = current_score;
    
    double temperature = 1.0;
    double cooling_rate = 0.99995;
    
    while(true) {
        auto current_time = chrono::high_resolution_clock::now();
        chrono::duration<double> elapsed = current_time - start_time;
        if (elapsed.count() > 59.0) { // Run for 59 seconds
            break;
        }
        
        int r = dist_row(rng);
        int c = dist_col(rng);
        int old_digit = grid[r][c];
        int new_digit = dist_digit(rng);
        if (old_digit == new_digit) continue;
        
        grid[r][c] = new_digit;
        
        int new_score = calculate_score();

        if (new_score > current_score) {
            current_score = new_score;
            if (current_score > best_score) {
                best_score = current_score;
                best_grid = grid;
            }
        } else {
            double acceptance_prob = exp((double)(new_score - current_score) / temperature);
            if (dist_prob(rng) < acceptance_prob) {
                current_score = new_score;
            } else {
                grid[r][c] = old_digit;
            }
        }
        
        temperature *= cooling_rate;
    }

    for (int r = 0; r < H; ++r) {
        for (int c = 0; c < W; ++c) {
            cout << best_grid[r][c];
        }
        cout << "\n";
    }

    return 0;
}