#include <iostream>
#include <vector>
#include <cmath>
#include <iomanip>
#include <map>
#include <tuple>
#include <algorithm>

const double PI = acos(-1.0);

struct Square {
    double x, y, a;
};

struct Solution {
    double L;
    std::vector<Square> squares;
};

std::map<int, Solution> memo;

Solution solve(int n);

Solution baseline_solver(int n) {
    if (n == 0) {
        return {0.0, {}};
    }
    double L = ceil(sqrt((double)n));
    std::vector<Square> squares;
    int k = static_cast<int>(L);
    for (int i = 0; i < n; ++i) {
        squares.push_back({(double)(i % k) + 0.5, (double)(i / k) + 0.5, 0.0});
    }
    return {L, squares};
}


Solution solve(int n) {
    if (memo.count(n)) {
        return memo.at(n);
    }
    
    if (n <= 4) {
        return memo[n] = baseline_solver(n);
    }

    long long k_sqrt = round(sqrt(n-1));
    if (k_sqrt * k_sqrt == n - 1 && k_sqrt == 2) { // n=5
        double L = 2.0 + sqrt(2.0) / 2.0;
        Solution res;
        res.L = L;
        res.squares.push_back({L / 2.0, L / 2.0, 45.0});
        res.squares.push_back({0.5, 0.5, 0});
        res.squares.push_back({L - 0.5, 0.5, 0});
        res.squares.push_back({0.5, L - 0.5, 0});
        res.squares.push_back({L - 0.5, L - 0.5, 0});
        
        Solution baseline_sol = baseline_solver(n);
        if (res.L < baseline_sol.L) {
          return memo[n] = res;
        }
    }

    int k = (n + 3) / 4; // ceil(n/4.0)
    
    Solution rec_sol;
    double L_k = solve(k).L;
    rec_sol.L = 2.0 * L_k;

    Solution baseline_sol = baseline_solver(n);

    if (rec_sol.L < baseline_sol.L) {
        std::vector<Square> squares;
        int rem = 4 * k - n;
        std::vector<int> sub_ns;
        for (int i = 0; i < 4 - rem; ++i) sub_ns.push_back(k);
        for (int i = 0; i < rem; ++i) sub_ns.push_back(k - 1);
        
        double s = solve(k).L;
        
        auto sub_k = solve(k);
        auto sub_k_1 = solve(k - 1);
        
        // BL
        const auto& sol0 = (sub_ns[0] == k) ? sub_k : sub_k_1;
        for(const auto& sq : sol0.squares) squares.push_back({sq.x, sq.y, sq.a});
        
        // BR
        const auto& sol1 = (sub_ns[1] == k) ? sub_k : sub_k_1;
        for(const auto& sq : sol1.squares) squares.push_back({sq.x + s, sq.y, sq.a});

        // TL
        const auto& sol2 = (sub_ns[2] == k) ? sub_k : sub_k_1;
        for(const auto& sq : sol2.squares) squares.push_back({sq.x, sq.y + s, sq.a});

        // TR
        const auto& sol3 = (sub_ns[3] == k) ? sub_k : sub_k_1;
        for(const auto& sq : sol3.squares) squares.push_back({sq.x + s, sq.y + s, sq.a});
        
        rec_sol.squares = squares;
        return memo[n] = rec_sol;

    } else {
        return memo[n] = baseline_sol;
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    int n;
    std::cin >> n;

    memo[0] = {0.0, {}};

    Solution result = solve(n);

    std::cout << std::fixed << std::setprecision(10) << result.L << std::endl;
    for (int i = 0; i < n; ++i) {
        std::cout << std::fixed << std::setprecision(10) << result.squares[i].x << " " << result.squares[i].y << " " << result.squares[i].a << std::endl;
    }

    return 0;
}