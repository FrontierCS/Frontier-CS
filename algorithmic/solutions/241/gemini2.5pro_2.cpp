#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <map>

using namespace std;

// Structure to hold an expression and its operator count
struct Result {
    string expr;
    int ops;

    // Comparison for finding the best result (min ops, then min length)
    bool operator<(const Result& other) const {
        if (ops != other.ops) {
            return ops < other.ops;
        }
        if (expr.length() != other.expr.length()) {
            return expr.length() < other.expr.length();
        }
        return expr < other.expr;
    }
};

// Memoization table for the recursive solver
map<string, Result> memo;

// Recursive function to find the optimal expression for a given truth table
Result solve(int n, const string& s) {
    // Base cases and memoization
    if (s.length() == 1) {
        return s == "0" ? Result{"F", 0} : Result{"T", 0};
    }
    if (memo.count(s)) {
        return memo[s];
    }

    bool all_zeros = true, all_ones = true;
    for (char c : s) {
        if (c == '0') all_ones = false;
        if (c == '1') all_zeros = false;
    }

    if (all_zeros) return memo[s] = {"F", 0};
    if (all_ones) return memo[s] = {"T", 0};
    
    Result best_res = {"", 1e9};

    // Try splitting on each variable to find the best decomposition
    for (int i = 0; i < n; ++i) {
        string s0_sub(1 << (n - 1), '0');
        string s1_sub(1 << (n - 1), '0');

        // Construct truth tables for subproblems f(..., v_i=0, ...) and f(..., v_i=1, ...)
        // The variables for the subproblem are mapped to a,b,c...
        for (int k = 0; k < (1 << (n - 1)); ++k) {
            int original_mask0 = 0;
            int p = 0;
            for (int bit_idx = 0; bit_idx < n; ++bit_idx) {
                if (i == bit_idx) continue;
                if ((k >> p) & 1) {
                    original_mask0 |= (1 << bit_idx);
                }
                p++;
            }
            int original_mask1 = original_mask0 | (1 << i);
            s0_sub[k] = s[original_mask0];
            s1_sub[k] = s[original_mask1];
        }

        Result res0 = solve(n - 1, s0_sub);
        Result res1 = solve(n - 1, s1_sub);

        // Remap variables from subproblem's 'a','b',... to original variable names
        string e0 = res0.expr;
        string e1 = res1.expr;
        for (int j = 0; j < n - 1; ++j) {
            char from = 'a' + j;
            char to = 'a' + (j < i ? j : j + 1);
            if (from != to) {
                replace(e0.begin(), e0.end(), from, to);
                replace(e1.begin(), e1.end(), from, to);
            }
        }
        
        string var_name(1, 'a' + i);

        // Try OR-decomposition: f = f0 | (v & f1)
        Result current_or;
        if (e0 == "T" || e1 == "F") {
            current_or = {e0, res0.ops};
        } else if (e0 == "F") {
            if (e1 == "T") {
                current_or = {var_name, 0};
            } else {
                current_or = {"(" + var_name + "&" + e1 + ")", res1.ops + 1};
            }
        } else if (e1 == "T") {
             current_or = {"(" + e0 + "|" + var_name + ")", res0.ops + 1};
        } else if (e0 == e1) {
            current_or = {e0, res0.ops};
        } else {
            current_or = {"(" + e0 + "|(" + var_name + "&" + e1 + "))", res0.ops + res1.ops + 2};
        }
        if (current_or < best_res) best_res = current_or;

        // Try AND-decomposition: f = f1 & (v | f0)
        Result current_and;
        if (e1 == "F" || e0 == "T") {
            current_and = {e1, res1.ops};
        } else if (e1 == "T") {
            if (e0 == "F") {
                current_and = {var_name, 0};
            } else {
                current_and = {"(" + var_name + "|" + e0 + ")", res0.ops + 1};
            }
        } else if (e0 == "F") {
            current_and = {"(" + e1 + "&" + var_name + ")", res1.ops + 1};
        } else if (e0 == e1) {
            current_and = {e1, res1.ops};
        } else {
            current_and = {"(" + e1 + "&(" + var_name + "|" + e0 + "))", res0.ops + res1.ops + 2};
        }
        if (current_and < best_res) best_res = current_and;
    }

    return memo[s] = best_res;
}

// A simpler, faster version of solve that only splits on the most significant variable.
// This is used for larger n to meet time limits, at the cost of optimality.
Result solve_simple(int n, const string& s) {
    if (memo.count(s)) {
        return memo[s];
    }
    bool all_zeros = true, all_ones = true;
    for (char c : s) {
        if (c == '0') all_ones = false;
        if (c == '1') all_zeros = false;
    }
    if (all_zeros) return memo[s] = {"F", 0};
    if (all_ones) return memo[s] = {"T", 0};
    if (n == 0) {
        return s == "0" ? Result{"F", 0} : Result{"T", 0};
    }
    
    string var(1, 'a' + n - 1);
    string s0 = s.substr(0, s.length() / 2);
    string s1 = s.substr(s.length() / 2);

    Result res0 = solve_simple(n - 1, s0);
    Result res1 = solve_simple(n - 1, s1);

    Result current_or;
    if (res0.expr == "T" || res1.expr == "F") {
        current_or = res0;
    } else if (res0.expr == "F") {
        if (res1.expr == "T") { current_or = {var, 0}; } 
        else { current_or = {"(" + var + "&" + res1.expr + ")", res1.ops + 1}; }
    } else if (res1.expr == "T") {
         current_or = {"(" + res0.expr + "|" + var + ")", res0.ops + 1};
    } else if (res0.expr == res1.expr) {
        current_or = res0;
    } else {
        current_or = {"(" + res0.expr + "|(" + var + "&" + res1.expr + "))", res0.ops + res1.ops + 2};
    }
    
    Result current_and;
    if (res1.expr == "F" || res0.expr == "T") {
        current_and = res1;
    } else if (res1.expr == "T") {
        if (res0.expr == "F") { current_and = {var, 0}; } 
        else { current_and = {"(" + var + "|" + res0.expr + ")", res0.ops + 1}; }
    } else if (res0.expr == "F") {
        current_and = {"(" + res1.expr + "&" + var + ")", res1.ops + 1};
    } else if (res0.expr == res1.expr) {
        current_and = res0;
    } else {
        current_and = {"(" + res1.expr + "&(" + var + "|" + res0.expr + "))", res0.ops + res1.ops + 2};
    }

    return memo[s] = min(current_or, current_and);
}

// Checks if a boolean function is monotone.
bool is_monotone(int n, const string& s) {
    if (n == 0) return true;
    int len = 1 << n;
    for (int i = 0; i < len; ++i) {
        for (int j = 0; j < n; ++j) {
            if (!((i >> j) & 1)) {
                int next_i = i | (1 << j);
                if (s[i] > s[next_i]) {
                    return false;
                }
            }
        }
    }
    return true;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int T;
    cin >> T;
    while (T--) {
        int n;
        cin >> n;
        string s;
        cin >> s;

        if (!is_monotone(n, s)) {
            cout << "No\n";
            continue;
        }

        cout << "Yes\n";
        memo.clear();
        
        // Use a hybrid strategy: a more optimal but slower solver for small n,
        // and a faster but less optimal one for larger n.
        if (n <= 5) {
             cout << solve(n,s).expr << "\n";
        } else {
             cout << solve_simple(n,s).expr << "\n";
        }
    }

    return 0;
}