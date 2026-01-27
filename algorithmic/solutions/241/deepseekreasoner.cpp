#include <bits/stdc++.h>
using namespace std;

int n;
string s;
unordered_map<string, pair<int, string>> memo;

// Compute the truth table string for the subfunction defined by fixed_mask and fixed_vals.
string get_key(int fixed_mask, int fixed_vals) {
    vector<int> free_vars;
    int fixed_bits = 0;
    for (int i = 0; i < n; ++i) {
        if (fixed_mask & (1 << i)) {
            if (fixed_vals & (1 << i))
                fixed_bits += (1 << i);
        } else {
            free_vars.push_back(i);
        }
    }
    int m = free_vars.size();
    string key(1 << m, '0');
    // iterate over all assignments to free variables
    for (int assig = 0; assig < (1 << m); ++assig) {
        int idx = fixed_bits;
        for (int k = 0; k < m; ++k) {
            if (assig & (1 << k))
                idx += (1 << free_vars[k]);
        }
        key[assig] = s[idx];
    }
    return key;
}

pair<int, string> solve(int fixed_mask, int fixed_vals) {
    string key = get_key(fixed_mask, fixed_vals);
    auto it = memo.find(key);
    if (it != memo.end()) return it->second;

    // get free variables again (needed for base cases and splitting)
    vector<int> free_vars;
    for (int i = 0; i < n; ++i) {
        if (!(fixed_mask & (1 << i)))
            free_vars.push_back(i);
    }
    int m = free_vars.size();

    // Check constant
    bool all0 = true, all1 = true;
    for (char c : key) {
        if (c == '0') all1 = false;
        else all0 = false;
    }
    if (all0) {
        memo[key] = {0, "F"};
        return {0, "F"};
    }
    if (all1) {
        memo[key] = {0, "T"};
        return {0, "T"};
    }

    // Check if the function is a single variable
    for (int i : free_vars) {
        int pos = find(free_vars.begin(), free_vars.end(), i) - free_vars.begin();
        bool match = true;
        for (int assig = 0; assig < (1 << m); ++assig) {
            char expected = ((assig >> pos) & 1) ? '1' : '0';
            if (key[assig] != expected) {
                match = false;
                break;
            }
        }
        if (match) {
            string var_str(1, 'a' + i);
            memo[key] = {0, var_str};
            return {0, var_str};
        }
    }

    int best_ops = INT_MAX;
    string best_expr;

    // Try splitting on each free variable
    for (int i : free_vars) {
        // fix variable i to 0
        int mask0 = fixed_mask | (1 << i);
        int vals0 = fixed_vals & ~(1 << i);
        auto [ops0, expr0] = solve(mask0, vals0);

        // fix variable i to 1
        int mask1 = fixed_mask | (1 << i);
        int vals1 = fixed_vals | (1 << i);
        auto [ops1, expr1] = solve(mask1, vals1);

        // Check if the two subfunctions are equal
        string key0 = get_key(mask0, vals0);
        string key1 = get_key(mask1, vals1);
        if (key0 == key1) {
            if (ops0 < best_ops) {
                best_ops = ops0;
                best_expr = expr0;
            }
            continue;
        }

        // Build candidate expression, applying simplifications
        int add_ops = 2;
        string expr;
        if (expr0 == "F") {
            expr = "(" + string(1, 'a' + i) + "&" + expr1 + ")";
            add_ops = 1;
        } else if (expr1 == "T") {
            expr = "(" + expr0 + "|" + string(1, 'a' + i) + ")";
            add_ops = 1;
        } else if (expr1 == "F") {
            expr = expr0;
            add_ops = 0;
        } else {
            expr = "(" + expr0 + "|(" + string(1, 'a' + i) + "&" + expr1 + "))";
        }
        int total_ops = ops0 + ops1 + add_ops;
        if (total_ops < best_ops) {
            best_ops = total_ops;
            best_expr = expr;
        }
    }

    memo[key] = {best_ops, best_expr};
    return {best_ops, best_expr};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    cin >> T;
    while (T--) {
        cin >> n;
        cin >> s;
        // s has length 2^n

        // Check monotonicity
        bool monotone = true;
        for (int x = 0; x < (1 << n); ++x) {
            for (int i = 0; i < n; ++i) {
                if (!((x >> i) & 1)) {
                    int y = x | (1 << i);
                    if (s[x] == '1' && s[y] == '0') {
                        monotone = false;
                        break;
                    }
                }
            }
            if (!monotone) break;
        }

        if (!monotone) {
            cout << "No\n";
            continue;
        }

        // Clear memo for this test case
        memo.clear();
        auto [ops, expr] = solve(0, 0);
        cout << "Yes\n" << expr << "\n";
    }
    return 0;
}