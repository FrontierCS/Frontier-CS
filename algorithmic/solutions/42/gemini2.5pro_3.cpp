#include <iostream>
#include <vector>
#include <cmath>
#include <iomanip>
#include <tuple>
#include <map>
#include <algorithm>
#include <numeric>

using namespace std;

struct Result {
    double L;
    vector<tuple<double, double, double>> squares;
};

map<int, Result> memo;

Result solve(int n) {
    if (memo.count(n)) {
        return memo[n];
    }

    if (n == 0) {
        return memo[n] = {0.0, {}};
    }
    if (n == 1) {
        return memo[n] = {1.0, {{0.5, 0.5, 0.0}}};
    }
    if (n <= 4) {
        Result res;
        res.L = 2.0;
        if (n == 2) {
            res.squares.emplace_back(0.5, 0.5, 0.0);
            res.squares.emplace_back(1.5, 0.5, 0.0);
        } else if (n == 3) {
            res.squares.emplace_back(0.5, 0.5, 0.0);
            res.squares.emplace_back(1.5, 0.5, 0.0);
            res.squares.emplace_back(0.5, 1.5, 0.0);
        } else if (n == 4) {
            res.squares.emplace_back(0.5, 0.5, 0.0);
            res.squares.emplace_back(1.5, 0.5, 0.0);
            res.squares.emplace_back(0.5, 1.5, 0.0);
            res.squares.emplace_back(1.5, 1.5, 0.0);
        }
        return memo[n] = res;
    }
    if (n == 5) {
        double L = 2.0 + 1.0 / sqrt(2.0);
        double s = 1.0 / (2.0 * sqrt(2.0));
        Result res;
        res.L = L;
        res.squares.emplace_back(0.5, 1.0 + s, 0.0);
        res.squares.emplace_back(1.0 + s, 0.5, 0.0);
        res.squares.emplace_back(L - 0.5, 1.0 + s, 0.0);
        res.squares.emplace_back(1.0 + s, L - 0.5, 0.0);
        res.squares.emplace_back(L / 2.0, L / 2.0, 45.0);
        return memo[n] = res;
    }
    if (n <= 9) {
        Result res;
        res.L = 3.0;
        int side = 3;
        int count = 0;
        for (int i = 0; i < side && count < n; ++i) {
            for (int j = 0; j < side && count < n; ++j) {
                res.squares.emplace_back(j + 0.5, i + 0.5, 0.0);
                count++;
            }
        }
        return memo[n] = res;
    }

    int n1 = (n + 3) / 4;
    int n2 = (n + 2) / 4;
    int n3 = (n + 1) / 4;
    int n4 = n / 4;

    vector<int> parts = {n1, n2, n3, n4};
    vector<Result> sub_results;
    for (int part : parts) {
        if (part > 0) {
            sub_results.push_back(solve(part));
        }
    }
    
    sort(sub_results.begin(), sub_results.end(), [](const Result& a, const Result& b) {
        return a.L > b.L;
    });

    while (sub_results.size() < 4) {
        sub_results.push_back({0.0, {}});
    }

    Result res;
    double La = sub_results[0].L;
    double Lb = sub_results[1].L;
    double Lc = sub_results[2].L;
    
    res.L = max(La + Lb, La + Lc);
    
    for (const auto& sq : sub_results[0].squares) {
        res.squares.emplace_back(get<0>(sq), get<1>(sq), get<2>(sq));
    }
    for (const auto& sq : sub_results[1].squares) {
        res.squares.emplace_back(get<0>(sq) + La, get<1>(sq), get<2>(sq));
    }
    for (const auto& sq : sub_results[2].squares) {
        res.squares.emplace_back(get<0>(sq), get<1>(sq) + La, get<2>(sq));
    }
    for (const auto& sq : sub_results[3].squares) {
        res.squares.emplace_back(get<0>(sq) + La, get<1>(sq) + La, get<2>(sq));
    }
    
    return memo[n] = res;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;

    Result result = solve(n);

    cout << fixed << setprecision(9) << result.L << endl;
    for (const auto& sq : result.squares) {
        cout << fixed << setprecision(9) << get<0>(sq) << " " << get<1>(sq) << " " << get<2>(sq) << endl;
    }

    return 0;
}