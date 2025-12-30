#include <iostream>
#include <vector>
#include <string>
#include <chrono>
#include <random>
#include <cmath>
#include <numeric>
#include <algorithm>

constexpr int R = 8;
constexpr int C = 14;

std::mt19937 rng;

class GridSolver {
private:
    std::vector<std::vector<int>> current_grid;
    std::vector<std::vector<int>> best_grid;
    int current_score;
    int best_score;

    // Buffers for is_readable to avoid reallocations
    std::vector<int> q, next_q;
    std::vector<bool> visited_level;

public:
    GridSolver() : visited_level(R * C, false) {
        current_grid.resize(R, std::vector<int>(C));
        std::uniform_int_distribution<int> dist(0, 9);
        for (int i = 0; i < R; ++i) {
            for (int j = 0; j < C; ++j) {
                current_grid[i][j] = dist(rng);
            }
        }
        best_grid = current_grid;
        current_score = calculate_score(current_grid);
        best_score = current_score;
    }

    bool is_readable(int k, const std::vector<std::vector<int>>& g) {
        std::string s = std::to_string(k);
        int target_digit = s[0] - '0';
        
        q.clear();
        for (int r = 0; r < R; ++r) {
            for (int c = 0; c < C; ++c) {
                if (g[r][c] == target_digit) {
                    q.push_back(r * C + c);
                }
            }
        }

        if (q.empty()) return false;

        for (size_t i = 1; i < s.length(); ++i) {
            target_digit = s[i] - '0';
            next_q.clear();
            std::fill(visited_level.begin(), visited_level.end(), false);

            for (const auto& p_flat : q) {
                int r = p_flat / C;
                int c = p_flat % C;
                for (int dr = -1; dr <= 1; ++dr) {
                    for (int dc = -1; dc <= 1; ++dc) {
                        if (dr == 0 && dc == 0) continue;
                        int nr = r + dr;
                        int nc = c + dc;
                        if (nr >= 0 && nr < R && nc >= 0 && nc < C) {
                            if (g[nr][nc] == target_digit) {
                                int flat_idx = nr * C + nc;
                                if (!visited_level[flat_idx]) {
                                    next_q.push_back(flat_idx);
                                    visited_level[flat_idx] = true;
                                }
                            }
                        }
                    }
                }
            }
            q = next_q;
            if (q.empty()) return false;
        }
        return true;
    }

    int calculate_score(const std::vector<std::vector<int>>& g) {
        for (int k = 1; ; ++k) {
            if (!is_readable(k, g)) {
                return k - 1;
            }
        }
    }

    void solve() {
        auto start_time = std::chrono::high_resolution_clock::now();
        const double time_limit = 58.0;

        std::uniform_int_distribution<int> row_dist(0, R - 1);
        std::uniform_int_distribution<int> col_dist(0, C - 1);
        std::uniform_int_distribution<int> dig_dist(0, 9);
        std::uniform_real_distribution<double> real_dist(0.0, 1.0);

        double initial_temp = 10.0;
        double final_temp = 0.01;

        while (true) {
            auto now = std::chrono::high_resolution_clock::now();
            double elapsed_time = std::chrono::duration<double>(now - start_time).count();
            if (elapsed_time > time_limit) {
                break;
            }
            
            double temp = initial_temp * std::pow(final_temp / initial_temp, elapsed_time / time_limit);
            if (temp < 1e-9) temp = 1e-9;

            int r = row_dist(rng);
            int c = col_dist(rng);
            int new_digit = dig_dist(rng);
            int old_digit = current_grid[r][c];

            if (new_digit == old_digit) continue;

            current_grid[r][c] = new_digit;
            int new_score = calculate_score(current_grid);

            double delta_score = static_cast<double>(new_score - current_score);
            if (delta_score > 0 || real_dist(rng) < exp(delta_score / temp)) {
                current_score = new_score;
                if (current_score > best_score) {
                    best_score = current_score;
                    best_grid = current_grid;
                }
            } else {
                current_grid[r][c] = old_digit;
            }
        }
        
        print_grid(best_grid);
    }

    void print_grid(const std::vector<std::vector<int>>& g) {
        for (int i = 0; i < R; ++i) {
            for (int j = 0; j < C; ++j) {
                std::cout << g[i][j];
            }
            std::cout << '\n';
        }
    }
};

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    rng.seed(std::chrono::high_resolution_clock::now().time_since_epoch().count());
    
    GridSolver solver;
    solver.solve();

    return 0;
}