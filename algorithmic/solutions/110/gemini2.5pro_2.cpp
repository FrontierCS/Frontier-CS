#include <iostream>
#include <vector>
#include <string>
#include <random>
#include <chrono>
#include <cmath>
#include <array>
#include <numeric>
#include <algorithm>

const int ROWS = 8;
const int COLS = 14;
const int CELLS = ROWS * COLS;

using Grid = std::array<int, CELLS>;

// Global precomputed data
std::vector<std::vector<int>> neighbors;
std::vector<std::string> num_to_str;

void precompute_neighbors() {
    neighbors.assign(CELLS, std::vector<int>());
    for (int r = 0; r < ROWS; ++r) {
        for (int c = 0; c < COLS; ++c) {
            int idx = r * COLS + c;
            for (int dr = -1; dr <= 1; ++dr) {
                for (int dc = -1; dc <= 1; ++dc) {
                    if (dr == 0 && dc == 0) continue;
                    int nr = r + dr;
                    int nc = c + dc;
                    if (nr >= 0 && nr < ROWS && nc >= 0 && nc < COLS) {
                        neighbors[idx].push_back(nr * COLS + nc);
                    }
                }
            }
        }
    }
}

void precompute_strings(int max_val) {
    num_to_str.resize(max_val + 1);
    for (int i = 1; i <= max_val; ++i) {
        num_to_str[i] = std::to_string(i);
    }
}

bool can_read(const Grid& grid, int x) {
    if (x <= 0 || static_cast<size_t>(x) >= num_to_str.size() || num_to_str[x].empty()) {
        return false;
    }
    const std::string& s = num_to_str[x];
    int len = s.length();

    std::vector<char> prev_dp(CELLS, 0);

    int d0 = s[0] - '0';
    for (int i = 0; i < CELLS; ++i) {
        if (grid[i] == d0) {
            prev_dp[i] = 1;
        }
    }

    for (int k = 1; k < len; ++k) {
        std::vector<char> curr_dp(CELLS, 0);
        int dk = s[k] - '0';
        bool possible_path = false;
        for (int i = 0; i < CELLS; ++i) {
            if (grid[i] == dk) {
                for (int neighbor_idx : neighbors[i]) {
                    if (prev_dp[neighbor_idx]) {
                        curr_dp[i] = 1;
                        possible_path = true;
                        break;
                    }
                }
            }
        }
        if (!possible_path) return false;
        prev_dp = std::move(curr_dp);
    }

    for (int i = 0; i < CELLS; ++i) {
        if (prev_dp[i]) return true;
    }
    return false;
}

int full_score(const Grid& grid) {
    for (int x = 1; ; ++x) {
        if (!can_read(grid, x)) {
            return x - 1;
        }
    }
}

int evaluate_from(const Grid& grid, int start_x) {
    int x = start_x;
    while (can_read(grid, x)) {
        x++;
    }
    return x - 1;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    auto start_time = std::chrono::steady_clock::now();
    std::mt19937 rng(start_time.time_since_epoch().count());
    
    precompute_neighbors();
    precompute_strings(20000); 

    Grid current_grid, best_grid;
    std::uniform_int_distribution<int> digit_dist(0, 9);
    for (int i = 0; i < CELLS; ++i) {
        current_grid[i] = digit_dist(rng);
    }

    int current_score = full_score(current_grid);
    best_grid = current_grid;
    int best_score = current_score;

    double T = 1.0;
    double cooling_rate = 0.99995;
    std::uniform_int_distribution<int> cell_dist(0, CELLS - 1);
    std::uniform_real_distribution<double> prob_dist(0.0, 1.0);

    while (std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::steady_clock::now() - start_time).count() < 58000) {
        Grid neighbor_grid = current_grid;
        int cell_idx = cell_dist(rng);
        int old_digit = neighbor_grid[cell_idx];
        int new_digit;
        do {
            new_digit = digit_dist(rng);
        } while (new_digit == old_digit);
        neighbor_grid[cell_idx] = new_digit;

        if (can_read(neighbor_grid, current_score + 1)) {
            int neighbor_score = evaluate_from(neighbor_grid, current_score + 1);
            current_grid = neighbor_grid;
            current_score = neighbor_score;
            if (current_score > best_score) {
                best_score = current_score;
                best_grid = neighbor_grid;
            }
        } else {
            double delta = -1.0; 
            if (prob_dist(rng) < exp(delta / T)) {
                current_grid = neighbor_grid;
                current_score = full_score(current_grid);
            }
        }
        
        T *= cooling_rate;
    }

    for (int r = 0; r < ROWS; ++r) {
        for (int c = 0; c < COLS; ++c) {
            std::cout << best_grid[r * COLS + c];
        }
        std::cout << '\n';
    }

    return 0;
}