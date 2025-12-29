#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <map>
#include <iomanip>

using namespace std;

// Structure to represent a unit square
struct Square {
    double x, y, a;
};

// Structure to hold the result of a packing
struct Result {
    double L;
    vector<Square> squares;
};

// Memoization map to store results for each n
map<int, Result> memo;

const double SQRT2 = sqrt(2.0);

// Baseline solution: Packs n squares in a grid of size ceil(sqrt(n))
Result solve_baseline(int n) {
    int k = 0;
    while (k * k < n) k++;
    double L = (double)k;
    vector<Square> sqs;
    sqs.reserve(n);
    int count = 0;
    for (int i = 0; i < k; ++i) {
        for (int j = 0; j < k; ++j) {
            if (count >= n) break;
            // Place square centered at grid coordinates
            sqs.push_back({0.5 + j, 0.5 + i, 0.0});
            count++;
        }
        if (count >= n) break;
    }
    return {L, sqs};
}

// Special optimized packing for n=5
// Uses a 2 + 1/sqrt(2) side length container which is ~2.707 < 3.0 (baseline)
Result solve_5() {
    double L = 2.0 + 1.0 / SQRT2;
    vector<Square> sqs;
    // 4 corners upright
    sqs.push_back({0.5, 0.5, 0.0});             // Bottom-Left
    sqs.push_back({L - 0.5, 0.5, 0.0});         // Bottom-Right
    sqs.push_back({0.5, L - 0.5, 0.0});         // Top-Left
    sqs.push_back({L - 0.5, L - 0.5, 0.0});     // Top-Right
    // Center square rotated 45 degrees
    sqs.push_back({L / 2.0, L / 2.0, 45.0});
    return {L, sqs};
}

// Recursive solver
Result solve(int n) {
    if (memo.count(n)) return memo[n];

    // Strategy 1: Baseline Grid
    Result best = solve_baseline(n);

    // Strategy 2: Special hardcoded patterns for small n
    if (n == 5) {
        Result r5 = solve_5();
        if (r5.L < best.L) best = r5;
    }

    // Strategy 3: Recursive Divide and Conquer
    // Split n into 4 roughly equal parts and arrange in 2x2 grid
    if (n >= 4) {
        // Compute split sizes: n1 >= n2 >= n3 >= n4 roughly
        int n1 = (n + 3) / 4;
        int rem = n - n1;
        int n2 = (rem + 2) / 3;
        rem -= n2;
        int n3 = (rem + 1) / 2;
        int n4 = rem - n3;

        // Recursively solve sub-problems
        Result r1 = solve(n1);
        Result r2 = solve(n2);
        Result r3 = solve(n3);
        Result r4 = solve(n4);

        // Arrangement Logic:
        // Divide container into 4 quadrants.
        // Left Column: Bottom (r3), Top (r1)
        // Right Column: Bottom (r4), Top (r2)
        // Widths
        double w_left = max(r3.L, r1.L);
        double w_right = max(r4.L, r2.L);
        // Heights
        double h_bottom = max(r3.L, r4.L);
        double h_top = max(r1.L, r2.L);

        // Total dimensions
        double total_W = w_left + w_right;
        double total_H = h_bottom + h_top;
        double L_rec = max(total_W, total_H);

        // Update if recursive solution is better
        if (L_rec < best.L - 1e-9) {
            vector<Square> combined;
            combined.reserve(n);

            // Add r3 (Bottom-Left)
            for (const auto& s : r3.squares) 
                combined.push_back(s);
            
            // Add r4 (Bottom-Right), shift X by w_left
            for (const auto& s : r4.squares) 
                combined.push_back({s.x + w_left, s.y, s.a});

            // Add r1 (Top-Left), shift Y by h_bottom
            for (const auto& s : r1.squares) 
                combined.push_back({s.x, s.y + h_bottom, s.a});

            // Add r2 (Top-Right), shift X by w_left, Y by h_bottom
            for (const auto& s : r2.squares) 
                combined.push_back({s.x + w_left, s.y + h_bottom, s.a});

            best = {L_rec, combined};
        }
    }

    return memo[n] = best;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (cin >> n) {
        Result res = solve(n);
        cout << fixed << setprecision(8) << res.L << "\n";
        for (const auto& s : res.squares) {
            cout << s.x << " " << s.y << " " << s.a << "\n";
        }
    }
    return 0;
}