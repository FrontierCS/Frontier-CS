#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <map>
#include <algorithm>
#include <vector>

using namespace std;

map<string, pair<string, int>> memo;

// Remaps variables from a template expression of n-1 variables to n variables,
// skipping the one at split_var_idx.
string remap_vars(const string& tpl, int split_var_idx) {
    string res = "";
    res.reserve(tpl.length());
    for (char c : tpl) {
        if (c >= 'a' && c <= 'z') {
            int var_idx_sub = c - 'a';
            if (var_idx_sub >= split_var_idx) {
                res += (char)('a' + var_idx_sub + 1);
            } else {
                res += c;
            }
        } else {
            res += c;
        }
    }
    return res;
}

// Generates truth tables for subproblems f(..., x_i=0, ...) and f(..., x_i=1, ...).
void get_subproblems(int n, const string& s, int i, string& s0, string& s1) {
    int len_sub = 1 << (n - 1);
    s0.resize(len_sub);
    s1.resize(len_sub);
    int mask_low = (1 << i) - 1;
    for (int k_sub = 0; k_sub < len_sub; ++k_sub) {
        int low_bits = k_sub & mask_low;
        int high_bits = (k_sub & ~mask_low) << 1;
        int k0 = high_bits | low_bits;
        int k1 = k0 | (1 << i);
        s0[k_sub] = s[k0];
        s1[k_sub] = s[k1];
    }
}

// Recursively solves for the minimal expression for a given truth table s.
pair<string, int> solve(const string& s) {
    if (memo.count(s)) {
        return memo[s];
    }

    int len = s.length();
    int n = 0;
    if (len > 1) {
        n = 31 - __builtin_clz(len);
    }

    bool all_zeros = true, all_ones = true;
    for (char c : s) {
        if (c == '1') all_zeros = false;
        if (c == '0') all_ones = false;
    }
    if (all_zeros) return memo[s] = {"F", 0};
    if (all_ones) return memo[s] = {"T", 0};

    if (n > 0) {
        for (int i = 0; i < n; ++i) {
            bool is_var_i = true;
            for (int k = 0; k < len; ++k) {
                if (((k >> i) & 1) != (s[k] - '0')) {
                    is_var_i = false;
                    break;
                }
            }
            if (is_var_i) {
                string var_name = "";
                var_name += (char)('a' + i);
                return memo[s] = {var_name, 0};
            }
        }
    }
    
    int min_ops = 1e9;
    string best_expr = "";

    for (int i = 0; i < n; ++i) {
        string s0, s1;
        get_subproblems(n, s, i, s0, s1);

        pair<string, int> res0_tpl = solve(s0);
        pair<string, int> res1_tpl = solve(s1);

        int size0 = res0_tpl.second;
        int size1 = res1_tpl.second;
        
        string var_name(1, (char)('a' + i));

        // Decomposition 1: ((v | E0) & E1)
        if (res0_tpl.first == "F") { // (v & E1)
            if (size1 + 1 < min_ops) {
                min_ops = size1 + 1;
                best_expr = "(" + var_name + "&" + remap_vars(res1_tpl.first, i) + ")";
            }
        } else if (res1_tpl.first == "T") { // (v | E0)
             if (size0 + 1 < min_ops) {
                min_ops = size0 + 1;
                best_expr = "(" + var_name + "|" + remap_vars(res0_tpl.first, i) + ")";
            }
        } else {
            if (size0 + size1 + 2 < min_ops) {
                min_ops = size0 + size1 + 2;
                best_expr = "((" + var_name + "|" + remap_vars(res0_tpl.first, i) + ")&" + remap_vars(res1_tpl.first, i) + ")";
            }
        }
        
        // Decomposition 2: ((v & E1) | E0)
        if (res0_tpl.first == "F") { // (v & E1)
            if (size1 + 1 < min_ops) {
                min_ops = size1 + 1;
                best_expr = "(" + var_name + "&" + remap_vars(res1_tpl.first, i) + ")";
            }
        } else if (res1_tpl.first == "T") { // (v | E0)
            if (size0 + 1 < min_ops) {
                min_ops = size0 + 1;
                best_expr = "(" + var_name + "|" + remap_vars(res0_tpl.first, i) + ")";
            }
        } else if (res0_tpl.first != "T" && res1_tpl.first != "F"){
            if (size0 + size1 + 2 < min_ops) {
                min_ops = size0 + size1 + 2;
                best_expr = "((" + var_name + "&" + remap_vars(res1_tpl.first, i) + ")|" + remap_vars(res0_tpl.first, i) + ")";
            }
        }
    }

    return memo[s] = {best_expr, min_ops};
}

bool check_monotone(int n, const string& s) {
    int len = 1 << n;
    for (int i = 0; i < n; ++i) {
        for (int k = 0; k < len; ++k) {
            if (!((k >> i) & 1)) {
                if (s[k] == '1' && s[k | (1 << i)] == '0') {
                    return false;
                }
            }
        }
    }
    return true;
}

void solve_case() {
    int n;
    cin >> n;
    string s;
    cin >> s;

    if (!check_monotone(n, s)) {
        cout << "No\n";
        return;
    }

    cout << "Yes\n";
    memo.clear();
    pair<string, int> result = solve(s);
    cout << result.first << "\n";
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    int T;
    cin >> T;
    while(T--) {
        solve_case();
    }
    return 0;
}