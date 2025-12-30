#include <iostream>
#include <vector>
#include <cmath>
#include <iomanip>
#include <map>
#include <algorithm>
#include <vector>

// Define a structure to hold the information for a unit square
struct Square {
    double x, y, a;
};

// Memoization table to store results for solved n
std::map<int, std::pair<double, std::vector<Square>>> memo;

// The main recursive solver function
std::pair<double, std::vector<Square>> solve(int n) {
    // If result is already memoized, return it
    if (memo.count(n)) {
        return memo[n];
    }

    // Base cases
    if (n == 0) {
        return {0.0, {}};
    }
    if (n == 1) {
        return {1.0, {{0.5, 0.5, 0.0}}};
    }

    // --- Candidate 1: Baseline grid packing ---
    double L_base = std::ceil(std::sqrt(static_cast<double>(n)));
    std::vector<Square> sol_base;
    sol_base.reserve(n);
    int grid_dim = static_cast<int>(L_base);
    int count = 0;
    for (int i = 0; i < grid_dim && count < n; ++i) {
        for (int j = 0; j < grid_dim && count < n; ++j) {
            sol_base.push_back({0.5 + j, 0.5 + i, 0.0});
            count++;
        }
    }
    
    std::pair<double, std::vector<Square>> best_solution = {L_base, sol_base};

    // --- Candidate 2: Recursive packing ---
    // This strategy builds a solution for n by tiling four solutions for ceil(n/4)
    if (n > 1) {
        int k_rec = (n + 3) / 4;
        auto sub_problem = solve(k_rec);
        double L_sub = sub_problem.first;
        const auto& sol_sub = sub_problem.second;
        
        double L_rec = 2.0 * L_sub;
        std::vector<Square> sol_rec;
        sol_rec.reserve(4 * sol_sub.size());

        // Tile four copies of the sub-problem solution
        for (const auto& s : sol_sub) { sol_rec.push_back({s.x, s.y, s.a}); }
        for (const auto& s : sol_sub) { sol_rec.push_back({s.x + L_sub, s.y, s.a}); }
        for (const auto& s : sol_sub) { sol_rec.push_back({s.x, s.y + L_sub, s.a}); }
        for (const auto& s : sol_sub) { sol_rec.push_back({s.x + L_sub, s.y + L_sub, s.a}); }
        
        sol_rec.resize(n); // We only need n squares

        if (L_rec < best_solution.first) {
            best_solution = {L_rec, sol_rec};
        }
    }

    // --- Candidate 3: Special case for n = k^2 + 1, where k is even and >= 2 ---
    // This is a known high-density packing
    int k_spec = static_cast<int>(std::floor(std::sqrt(static_cast<double>(n - 1))));
    if (k_spec >= 2 && k_spec % 2 == 0 && k_spec * k_spec + 1 == n) {
        double L_spec = k_spec + 1.0 / std::sqrt(2.0);
        if (L_spec < best_solution.first) {
            std::vector<Square> sol_spec;
            sol_spec.reserve(n);
            sol_spec.push_back({L_spec / 2.0, L_spec / 2.0, 45.0});
            
            int half_k = k_spec / 2;
            // Bottom-left k/2 x k/2 block
            for (int i = 0; i < half_k; ++i) {
                for (int j = 0; j < half_k; ++j) {
                    sol_spec.push_back({0.5 + j, 0.5 + i, 0.0});
                }
            }
            // Bottom-right
            for (int i = 0; i < half_k; ++i) {
                for (int j = 0; j < half_k; ++j) {
                    sol_spec.push_back({L_spec - half_k + 0.5 + j, 0.5 + i, 0.0});
                }
            }
            // Top-left
            for (int i = 0; i < half_k; ++i) {
                for (int j = 0; j < half_k; ++j) {
                    sol_spec.push_back({0.5 + j, L_spec - half_k + 0.5 + i, 0.0});
                }
            }
            // Top-right
            for (int i = 0; i < half_k; ++i) {
                for (int j = 0; j < half_k; ++j) {
                    sol_spec.push_back({L_spec - half_k + 0.5 + j, L_spec - half_k + 0.5 + i, 0.0});
                }
            }
            best_solution = {L_spec, sol_spec};
        }
    }

    // Memoize and return the best solution found
    return memo[n] = best_solution;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    auto result = solve(n);

    std::cout << std::fixed << std::setprecision(10) << result.first << std::endl;
    for (const auto& s : result.second) {
        std::cout << std::fixed << std::setprecision(10) << s.x << " " << s.y << " " << s.a << std::endl;
    }

    return 0;
}