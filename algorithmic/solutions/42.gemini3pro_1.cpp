#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <iomanip>
#include <map>

using namespace std;

// Structure to represent a placed unit square
struct Square {
    double x, y, a;
};

// Structure to represent a packing solution
struct Solution {
    double L;
    vector<Square> squares;
};

// Memoization to store best solutions for n
map<int, Solution> memo;

// Generates a simple grid packing
Solution solve_grid(int n) {
    int k = (int)ceil(sqrt((double)n));
    double L = (double)k;
    vector<Square> sqs;
    sqs.reserve(n);
    int count = 0;
    for (int row = 0; row < k; ++row) {
        for (int col = 0; col < k; ++col) {
            if (count >= n) break;
            // Center of square at (col + 0.5, row + 0.5)
            sqs.push_back({col + 0.5, row + 0.5, 0.0});
            count++;
        }
        if (count >= n) break;
    }
    return {L, sqs};
}

// Generates the optimal packing for n=5
Solution solve_special_5() {
    double L = 2.0 + 1.0 / sqrt(2.0);
    vector<Square> sqs;
    // 4 unrotated squares in corners
    sqs.push_back({0.5, 0.5, 0.0});
    sqs.push_back({L - 0.5, 0.5, 0.0});
    sqs.push_back({0.5, L - 0.5, 0.0});
    sqs.push_back({L - 0.5, L - 0.5, 0.0});
    // 1 rotated square in center
    sqs.push_back({L / 2.0, L / 2.0, 45.0});
    return {L, sqs};
}

// Recursive solver
Solution solve(int n) {
    if (n == 0) return {0.0, {}};
    if (memo.count(n)) return memo[n];

    // Strategy 1: Baseline Grid
    Solution best = solve_grid(n);

    // Strategy 2: Special case for n=5
    if (n == 5) {
        Solution s5 = solve_special_5();
        if (s5.L < best.L) {
            best = s5;
        }
    }

    // Strategy 3: Recursive Quad Split
    if (n > 1) {
        // Split n into 4 parts as balanced as possible
        int q = n / 4;
        int r = n % 4;
        int ns[4];
        for (int i = 0; i < 4; ++i) {
            ns[i] = q + (i < r ? 1 : 0);
        }

        // Solve subproblems
        vector<Solution> subs;
        for (int i = 0; i < 4; ++i) {
            if (ns[i] > 0)
                subs.push_back(solve(ns[i]));
            else
                subs.push_back({0.0, {}});
        }

        // Try to pack the 4 sub-solutions into a larger square.
        // We use a "shelf" layout: 2 sub-solutions on bottom, 2 on top.
        // We try different pairings of the 4 parts.
        int pairings[3][4] = {
            {0, 1, 2, 3}, // Bottom: 0,1; Top: 2,3
            {0, 2, 1, 3}, // Bottom: 0,2; Top: 1,3
            {0, 3, 1, 2}  // Bottom: 0,3; Top: 1,2
        };

        for (int p = 0; p < 3; ++p) {
            int iA = pairings[p][0];
            int iB = pairings[p][1];
            int iC = pairings[p][2];
            int iD = pairings[p][3];

            double LA = subs[iA].L;
            double LB = subs[iB].L;
            double LC = subs[iC].L;
            double LD = subs[iD].L;

            // Calculate dimensions of the two rows
            double w_bottom = LA + LB;
            double h_bottom = max(LA, LB);
            
            double w_top = LC + LD;
            double h_top = max(LC, LD);

            // Total container dimensions
            double W = max(w_bottom, w_top);
            double H = h_bottom + h_top;
            double L_total = max(W, H);

            // If this recursive composition is better, update best
            if (L_total < best.L - 1e-9) { 
                vector<Square> new_sqs;
                new_sqs.reserve(n);

                auto add_squares = [&](const Solution& sol, double dx, double dy) {
                    for (const auto& sq : sol.squares) {
                        new_sqs.push_back({sq.x + dx, sq.y + dy, sq.a});
                    }
                };

                // Row 1 (Bottom)
                add_squares(subs[iA], 0.0, 0.0);
                add_squares(subs[iB], LA, 0.0);
                
                // Row 2 (Top) - placed above height of bottom row
                add_squares(subs[iC], 0.0, h_bottom);
                add_squares(subs[iD], LC, h_bottom);

                best = {L_total, new_sqs};
            }
        }
    }

    return memo[n] = best;
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (cin >> n) {
        Solution sol = solve(n);

        cout << fixed << setprecision(8);
        cout << sol.L << "\n";
        for (const auto& sq : sol.squares) {
            cout << sq.x << " " << sq.y << " " << sq.a << "\n";
        }
    }

    return 0;
}