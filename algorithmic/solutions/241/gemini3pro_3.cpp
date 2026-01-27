#include <iostream>
#include <vector>
#include <string>
#include <map>
#include <algorithm>

using namespace std;

// Fast I/O
void fast_io() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
}

// Global memoization table
// Key: truth table string
// Value: {cost, template_expression}
// Cost is number of & and | operators.
// Expression uses characters (char)('0'+i) to represent the i-th variable in the current scope.
map<string, pair<int, string>> memo;

// Helper to check monotonicity
// Returns true if monotone, false otherwise
bool is_monotone(int n, const string& s) {
    int len = s.length();
    // Check for each variable
    for (int i = 0; i < n; ++i) {
        int stride = 1 << i;
        for (int j = 0; j < len; ++j) {
            if ((j & stride) == 0) {
                // j has 0 at i-th bit, j + stride has 1
                if (s[j] == '1' && s[j + stride] == '0') {
                    return false;
                }
            }
        }
    }
    return true;
}

// Check if a variable is redundant
// var_idx is from 0 to k-1 (relative to current string size 2^k)
bool is_redundant(const string& s, int k, int var_idx) {
    int len = s.length();
    int stride = 1 << var_idx;
    for (int j = 0; j < len; ++j) {
        if ((j & stride) == 0) {
            if (s[j] != s[j + stride]) return false;
        }
    }
    return true;
}

// Reduce string by removing redundant variable
string reduce_string(const string& s, int k, int var_idx) {
    string res;
    res.reserve(s.length() / 2);
    int stride = 1 << var_idx;
    for (int j = 0; j < s.length(); ++j) {
        if ((j & stride) == 0) {
            res.push_back(s[j]);
        }
    }
    return res;
}

// Function to shift variable indices in an expression
// variables >= split_idx are incremented by 1
string shift_vars(const string& expr, int split_idx) {
    string res;
    res.reserve(expr.length());
    for (char c : expr) {
        // Variables are encoded as '0' + index. Check range carefully.
        // Assuming n <= 15, indices are 0..14. '0'..'>'.
        // We check if it is in the range of our variable encoding.
        if (c >= '0' && c <= '9' + 20) { 
            int idx = c - '0';
            if (idx >= split_idx) {
                res.push_back((char)('0' + idx + 1));
            } else {
                res.push_back(c);
            }
        } else {
            res.push_back(c);
        }
    }
    return res;
}

// Helper to get sub-table when variable var_idx is set to val (0 or 1)
string get_sub_table(const string& s, int var_idx, int val) {
    string res;
    res.reserve(s.length() / 2);
    int stride = 1 << var_idx;
    for (int j = 0; j < s.length(); ++j) {
        bool bit = (j & stride);
        if (bit == (bool)val) {
            res.push_back(s[j]);
        }
    }
    return res;
}

// Recursive solver
// Returns {cost, expression}
// Expression uses '0', '1', ... for variables
pair<int, string> solve(string s) {
    // Check memo
    if (memo.count(s)) return memo[s];

    int len = s.length();
    // Base cases
    bool all0 = true;
    bool all1 = true;
    for (char c : s) {
        if (c == '1') all0 = false;
        else all1 = false;
    }

    if (all0) return memo[s] = {0, "F"};
    if (all1) return memo[s] = {0, "T"};

    int k = 0;
    while ((1 << k) < len) k++;

    // Try to remove redundant variables to canonicalize
    for (int i = 0; i < k; ++i) {
        if (is_redundant(s, k, i)) {
            string reduced = reduce_string(s, k, i);
            pair<int, string> res = solve(reduced);
            // Shift variables in result: variables >= i need to be shifted up
            string shifted_expr = shift_vars(res.second, i);
            return memo[s] = {res.first, shifted_expr};
        }
    }

    // Try splitting on each variable
    int best_cost = 2e9;
    string best_expr = "";

    // We can split on any variable i in 0..k-1
    for (int i = 0; i < k; ++i) {
        string s0 = get_sub_table(s, i, 0);
        string s1 = get_sub_table(s, i, 1);
        
        pair<int, string> res0 = solve(s0);
        pair<int, string> res1 = solve(s1);
        
        int current_cost = 2e9;
        string current_expr = "";
        
        string var_str;
        var_str.push_back((char)('0' + i));

        // Lift sub-expressions indices
        string e0 = shift_vars(res0.second, i);
        string e1 = shift_vars(res1.second, i);

        // Shannon expansion: f = (x & f1) | f0  (since monotone f0 <= f1)
        
        bool f0_is_F = (e0 == "F");
        bool f1_is_T = (e1 == "T");
        
        if (f0_is_F && f1_is_T) {
             current_cost = 0;
             current_expr = var_str;
        } else if (f0_is_F) {
            current_cost = res1.first + 1;
            current_expr = "(" + var_str + "&" + e1 + ")";
        } else if (f1_is_T) {
            current_cost = res0.first + 1;
            current_expr = "(" + var_str + "|" + e0 + ")";
        } else {
            current_cost = res0.first + res1.first + 2;
            current_expr = "((" + var_str + "&" + e1 + ")|" + e0 + ")";
        }
        
        if (current_cost < best_cost) {
            best_cost = current_cost;
            best_expr = current_expr;
        }
    }
    
    return memo[s] = {best_cost, best_expr};
}

void run_test_case() {
    int n;
    if (!(cin >> n)) return;
    string s;
    cin >> s;

    if (!is_monotone(n, s)) {
        cout << "No\n";
        return;
    }

    cout << "Yes\n";
    memo.clear();
    
    pair<int, string> res = solve(s);
    string expr = res.second;
    
    // Map internal variables '0'..'9'.. to 'a'..'z'
    string final_expr;
    final_expr.reserve(expr.length());
    for (char c : expr) {
        if (c >= '0' && c <= '9' + 20) {
            int idx = c - '0';
            final_expr.push_back((char)('a' + idx));
        } else {
            final_expr.push_back(c);
        }
    }
    cout << final_expr << "\n";
}

int main() {
    fast_io();
    int t;
    if (cin >> t) {
        while (t--) {
            run_test_case();
        }
    }
    return 0;
}