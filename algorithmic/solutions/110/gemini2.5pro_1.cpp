#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <random>
#include <chrono>
#include <cmath>

const int R = 8;
const int C = 14;

using Grid = std::vector<std::vector<int>>;

const int dr[] = {-1, -1, -1, 0, 0, 1, 1, 1};
const int dc[] = {-1, 0, 1, -1, 1, -1, 0, 1};

bool can_read(const Grid& grid, int n) {
    std::string s = std::to_string(n);
    int len = s.length();
    
    std::vector<std::vector<bool>> dp(R, std::vector<bool>(C, false));

    int first_digit = s[0] - '0';
    bool possible_start = false;
    for (int r = 0; r < R; ++r) {
        for (int c = 0; c < C; ++c) {
            if (grid[r][c] == first_digit) {
                dp[r][c] = true;
                possible_start = true;
            }
        }
    }

    if (!possible_start) {
        return false;
    }
    if (len == 1) {
        return true;
    }

    for (int k = 1; k < len; ++k) {
        std::vector<std::vector<bool>> next_dp(R, std::vector<bool>(C, false));
        int digit = s[k] - '0';
        bool found_path_for_prefix = false;
        for (int r = 0; r < R; ++r) {
            for (int c = 0; c < C; ++c) {
                if (grid[r][c] == digit) {
                    for (int i = 0; i < 8; ++i) {
                        int pr = r + dr[i];
                        int pc = c + dc[i];
                        if (pr >= 0 && pr < R && pc >= 0 && pc < C && dp[pr][pc]) {
                            next_dp[r][c] = true;
                            found_path_for_prefix = true;
                            break;
                        }
                    }
                }
            }
        }
        if (!found_path_for_prefix) {
            return false;
        }
        dp = next_dp;
    }

    return true;
}

int calculate_score(const Grid& grid) {
    int x = 1;
    while (can_read(grid, x)) {
        x++;
    }
    return x - 1;
}

int main() {
    std::ios_base::sync_with_stdio(false);

    auto start_time = std::chrono::high_resolution_clock::now();
    long long time_limit_ms = 58000; // Run for 58 seconds

    std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());

    Grid current_grid(R, std::vector<int>(C));
    for (int r = 0; r < R; ++r) {
        for (int c = 0; c < C; ++c) {
            current_grid[r][c] = std::uniform_int_distribution<int>(0, 9)(rng);
        }
    }
    
    int current_score = calculate_score(current_grid);
    
    Grid best_grid = current_grid;
    int best_score = current_score;

    double temperature = 5.0;
    double cooling_rate = 0.99995;

    std::uniform_int_distribution<int> r_dist(0, R - 1);
    std::uniform_int_distribution<int> c_dist(0, C - 1);
    std::uniform_int_distribution<int> d_dist(0, 9);
    std::uniform_real_distribution<double> p_dist(0.0, 1.0);

    while (std::chrono::duration_cast<std::chrono::milliseconds>(std::chrono::high_resolution_clock::now() - start_time).count() < time_limit_ms) {
        Grid next_grid = current_grid;
        
        int r = r_dist(rng);
        int c = c_dist(rng);
        int old_digit = next_grid[r][c];
        int new_digit = d_dist(rng);
        while (new_digit == old_digit) {
            new_digit = d_dist(rng);
        }
        next_grid[r][c] = new_digit;
        
        int next_score = calculate_score(next_grid);
        
        if (next_score > best_score) {
            best_score = next_score;
            best_grid = next_grid;
        }

        if (next_score > current_score) {
            current_grid = next_grid;
            current_score = next_score;
        } else {
            if (temperature > 1e-9) {
                 double acceptance_prob = exp((double)(next_score - current_score) / temperature);
                 if (p_dist(rng) < acceptance_prob) {
                    current_grid = next_grid;
                    current_score = next_score;
                }
            }
        }

        temperature *= cooling_rate;
    }
    
    for (int r = 0; r < R; ++r) {
        for (int c = 0; c < C; ++c) {
            std::cout << best_grid[r][c];
        }
        std::cout << '\n';
    }

    return 0;
}