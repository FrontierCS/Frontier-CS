#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <map>

using namespace std;

struct Result {
    string expr;
    int ops;
};

map<string, Result> memo;

Result build_or(const Result& r1, const Result& r2) {
    if (r1.expr == "T" || r2.expr == "T") return {"T", 0};
    if (r1.expr == "F") return r2;
    if (r2.expr == "F") return r1;
    if (r1.expr == r2.expr) return r1;
    return {"(" + r1.expr + "|" + r2.expr + ")", r1.ops + r2.ops + 1};
}

Result build_and(const Result& r1, const Result& r2) {
    if (r1.expr == "F" || r2.expr == "F") return {"F", 0};
    if (r1.expr == "T") return r2;
    if (r2.expr == "T") return r1;
    if (r1.expr == r2.expr) return r1;
    return {"(" + r1.expr + "&" + r2.expr + ")", r1.ops + r2.ops + 1};
}

Result solve(int n, const string& s) {
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
    
    if (n == 1) {
        return memo[s] = {string(1, 'a'), 0};
    }

    // Check for independence first, this is a powerful simplification
    for (int i = 0; i < n; ++i) { // variable 'a' + i
        bool independent = true;
        int step = 1 << i;
        for (int mask = 0; mask < (1 << n); ++mask) {
            if (!((mask >> i) & 1)) {
                if (s[mask] != s[mask | step]) {
                    independent = false;
                    break;
                }
            }
        }

        if (independent) {
            string s_new(1 << (n - 1), ' ');
            for (int j = 0; j < (1 << (n - 1)); ++j) {
                int low_mask = j & (step - 1);
                int high_mask = (j >> i) << (i + 1);
                s_new[j] = s[high_mask | low_mask];
            }
            
            Result sub_res = solve(n - 1, s_new);
            string new_expr;
            for (char c : sub_res.expr) {
                if (islower(c)) {
                    int var_idx = c - 'a';
                    if (var_idx >= i) {
                        new_expr += (char)('a' + var_idx + 1);
                    } else {
                        new_expr += c;
                    }
                } else {
                    new_expr += c;
                }
            }
            return memo[s] = {new_expr, sub_res.ops};
        }
    }

    // Splitting phase
    Result best_res = {"", 1000000000};
    for (int i = 0; i < n; ++i) { // split on var 'a' + i
        string s0(1 << (n - 1), ' ');
        string s1(1 << (n - 1), ' ');
        int step = 1 << i;

        for (int j = 0; j < (1 << (n - 1)); ++j) {
            int low_mask = j & (step - 1);
            int high_mask = (j >> i) << (i + 1);
            s0[j] = s[high_mask | low_mask];
            s1[j] = s[high_mask | low_mask | step];
        }

        Result r0 = solve(n - 1, s0);
        Result r1 = solve(n - 1, s1);

        string expr0 = r0.expr;
        string expr1 = r1.expr;

        string renamed_expr0, renamed_expr1;
        for (char c : expr0) {
            if (islower(c)) {
                int var_idx = c - 'a';
                if (var_idx >= i) renamed_expr0 += (char)('a' + var_idx + 1);
                else renamed_expr0 += c;
            } else renamed_expr0 += c;
        }
        for (char c : expr1) {
            if (islower(c)) {
                int var_idx = c - 'a';
                if (var_idx >= i) renamed_expr1 += (char)('a' + var_idx + 1);
                else renamed_expr1 += c;
            } else renamed_expr1 += c;
        }

        Result rr0 = {renamed_expr0, r0.ops};
        Result rr1 = {renamed_expr1, r1.ops};
        
        string var_name(1, 'a' + i);
        Result var_res = {var_name, 0};

        Result cand1 = build_or(rr0, build_and(var_res, rr1));
        Result cand2 = build_and(build_or(rr0, var_res), rr1);

        Result current_best;
        if (cand1.ops < cand2.ops) {
            current_best = cand1;
        } else if (cand2.ops < cand1.ops) {
            current_best = cand2;
        } else {
            current_best = cand1.expr.length() <= cand2.expr.length() ? cand1 : cand2;
        }

        if (current_best.ops < best_res.ops) {
            best_res = current_best;
        } else if (current_best.ops == best_res.ops && current_best.expr.length() < best_res.expr.length()) {
            best_res = current_best;
        }
    }
    
    return memo[s] = best_res;
}

void do_test_case() {
    int n;
    cin >> n;
    string s;
    cin >> s;

    // Check monotonicity
    bool monotone = true;
    for (int i = 0; i < n; ++i) {
        for (int mask = 0; mask < (1 << n); ++mask) {
            if (!((mask >> i) & 1)) {
                if (s[mask] > s[mask | (1 << i)]) {
                    monotone = false;
                    break;
                }
            }
        }
        if (!monotone) break;
    }

    if (!monotone) {
        cout << "No\n";
        return;
    }

    cout << "Yes\n";
    memo.clear();
    cout << solve(n, s).expr << "\n";
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int T;
    cin >> T;
    while (T--) {
        do_test_case();
    }
    return 0;
}