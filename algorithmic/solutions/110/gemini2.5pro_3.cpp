#include <iostream>
#include <vector>
#include <string>
#include <random>
#include <chrono>
#include <cmath>
#include <algorithm>
#include <numeric>

namespace {

const int ROWS = 8;
const int COLS = 14;

const int dr[] = {-1, -1, -1, 0, 0, 1, 1, 1};
const int dc[] = {-1, 0, 1, -1, 1, -1, 0, 1};

using Grid = std::vector<std::vector<int>>;

std::vector<std::vector<std::vector<char>>> memo;
const Grid* g_grid_ptr;

bool solve(const std::vector<int>& digits, int index, int r, int c) {
    if ((*g_grid_ptr)[r][c] != digits[index]) {
        return false;
    }
    if (index == digits.size() - 1) {
        return true;
    }
    if (memo[index][r][c] != -1) {
        return memo[index][r][c] == 1;
    }

    for (int i = 0; i < 8; ++i) {
        int nr = r + dr[i];
        int nc = c + dc[i];
        if (nr >= 0 && nr < ROWS && nc >= 0 && nc < COLS) {
            if (solve(digits, index + 1, nr, nc)) {
                memo[index][r][c] = 1;
                return true;
            }
        }
    }
    
    memo[index][r][c] = 0;
    return false;
}

bool is_readable(int k, const Grid& grid) {
    if (k <= 0) return true;
    std::string s = std::to_string(k);
    std::vector<int> digits;
    digits.reserve(s.length());
    for (char ch : s) {
        digits.push_back(ch - '0');
    }

    memo.assign(digits.size(), std::vector<std::vector<char>>(ROWS, std::vector<char>(COLS, -1)));
    g_grid_ptr = &grid;

    for (int r = 0; r < ROWS; ++r) {
        for (int c = 0; c < COLS; ++c) {
            if (solve(digits, 0, r, c)) {
                return true;
            }
        }
    }
    return false;
}

int calculate_score(const Grid& grid) {
    int x = 0;
    while (is_readable(x + 1, grid)) {
        x++;
    }
    return x;
}

void print_grid(const Grid& grid) {
    for (int r = 0; r < ROWS; ++r) {
        for (int c = 0; c < COLS; ++c) {
            std::cout << grid[r][c];
        }
        std::cout << '\n';
    }
}

}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(nullptr);

    auto seed = std::chrono::high_resolution_clock::now().time_since_epoch().count();
    std::mt19937 rng(seed);
    std::uniform_int_distribution<int> row_dist(0, ROWS - 1);
    std::uniform_int_distribution<int> col_dist(0, COLS - 1);
    std::uniform_real_distribution<double> prob_dist(0.0, 1.0);

    Grid current_grid(ROWS, std::vector<int>(COLS));
    std::vector<int> digits_pool;
    digits_pool.reserve(ROWS * COLS);
    for (int d = 0; d < 10; ++d) {
        for (int i = 0; i < (ROWS * COLS) / 10; ++i) {
            digits_pool.push_back(d);
        }
    }
    while (digits_pool.size() < ROWS * COLS) {
        digits_pool.push_back(digits_pool.size() % 10);
    }
    std::shuffle(digits_pool.begin(), digits_pool.end(), rng);
    
    int k = 0;
    for (int r = 0; r < ROWS; ++r) {
        for (int c = 0; c < COLS; ++c) {
            current_grid[r][c] = digits_pool[k++];
        }
    }

    int current_score = calculate_score(current_grid);
    Grid best_grid = current_grid;
    int best_score = current_score;

    double temperature = 1.0;
    double cooling_rate = 0.99995;
    
    auto start_time = std::chrono::high_resolution_clock::now();
    double time_limit_seconds = 58.0;

    while (true) {
        auto current_time = std::chrono::high_resolution_clock::now();
        if (std::chrono::duration<double>(current_time - start_time).count() > time_limit_seconds) {
            break;
        }

        Grid new_grid = current_grid;

        int r1 = row_dist(rng);
        int c1 = col_dist(rng);
        int r2, c2;
        do {
            r2 = row_dist(rng);
            c2 = col_dist(rng);
        } while (r1 == r2 && c1 == c2);
        
        std::swap(new_grid[r1][c1], new_grid[r2][c2]);

        int new_score = calculate_score(new_grid);
        
        if (new_score > current_score || (temperature > 1e-9 && prob_dist(rng) < std::exp((double)(new_score - current_score) / temperature))) {
            current_grid = new_grid;
            current_score = new_score;
        }
        
        if (current_score > best_score) {
            best_grid = current_grid;
            best_score = current_score;
        }

        temperature *= cooling_rate;
    }

    print_grid(best_grid);

    return 0;
}