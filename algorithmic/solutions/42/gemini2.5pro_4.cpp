#include <iostream>
#include <vector>
#include <cmath>
#include <iomanip>
#include <map>
#include <algorithm>

struct Square {
    double x, y, a;
};

std::map<int, std::pair<double, std::vector<Square>>> memo;

std::pair<double, std::vector<Square>> solve(int n) {
    if (n == 0) {
        return {0.0, {}};
    }
    if (memo.count(n)) {
        return memo[n];
    }

    // Special case for n=5, which is better than grid packing and seeds the recursion.
    if (n == 5) {
        double L = 2.0 + 1.0 / sqrt(2.0);
        double c = L / 2.0;
        std::vector<Square> squares;
        squares.push_back({c, c, 45.0});
        double offset = 0.5 + 1.0 / (2.0 * sqrt(2.0));
        squares.push_back({c - offset, c - offset, 0.0});
        squares.push_back({c - offset, c + offset, 0.0});
        squares.push_back({c + offset, c - offset, 0.0});
        squares.push_back({c + offset, c + offset, 0.0});
        return memo[n] = {L, squares};
    }
    
    // Baseline grid packing
    double L_grid = ceil(sqrt((double)n));
    std::vector<Square> grid_squares;
    int m = static_cast<int>(L_grid);
    int current_n = 0;
    for (int i = 0; i < m && current_n < n; ++i) {
        for (int j = 0; j < m && current_n < n; ++j) {
            grid_squares.push_back({0.5 + j, 0.5 + i, 0.0});
            current_n++;
        }
    }

    // For small n, grid packing is optimal or near-optimal.
    if (n <= 4) {
        return memo[n] = {L_grid, grid_squares};
    }

    // Recursive step
    int k = (n + 3) / 4; // ceil(n/4)
    auto sub_problem = solve(k);
    double L_k = sub_problem.first;
    const auto& squares_k = sub_problem.second;

    double L_rec = 2.0 * L_k;

    if (L_grid <= L_rec) {
        return memo[n] = {L_grid, grid_squares};
    }

    // Construct recursive solution
    std::vector<Square> rec_squares;
    
    int q_counts[4];
    q_counts[0] = n / 4;
    q_counts[1] = n / 4;
    q_counts[2] = n / 4;
    q_counts[3] = n / 4;
    int rem = n % 4;
    for (int i = 0; i < rem; ++i) {
        q_counts[i]++;
    }

    for (int i = 0; i < q_counts[0]; ++i) { // Bottom-left
        rec_squares.push_back({squares_k[i].x, squares_k[i].y, squares_k[i].a});
    }
    for (int i = 0; i < q_counts[1]; ++i) { // Bottom-right
        rec_squares.push_back({squares_k[i].x + L_k, squares_k[i].y, squares_k[i].a});
    }
    for (int i = 0; i < q_counts[2]; ++i) { // Top-left
        rec_squares.push_back({squares_k[i].x, squares_k[i].y + L_k, squares_k[i].a});
    }
    for (int i = 0; i < q_counts[3]; ++i) { // Top-right
        rec_squares.push_back({squares_k[i].x + L_k, squares_k[i].y + L_k, squares_k[i].a});
    }
    
    return memo[n] = {L_rec, rec_squares};
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    int n;
    std::cin >> n;

    auto result = solve(n);
    double L = result.first;
    const auto& squares = result.second;

    std::cout << std::fixed << std::setprecision(8) << L << "\n";
    for (const auto& s : squares) {
        std::cout << std::fixed << std::setprecision(8) << s.x << " " << s.y << " " << s.a << "\n";
    }

    return 0;
}