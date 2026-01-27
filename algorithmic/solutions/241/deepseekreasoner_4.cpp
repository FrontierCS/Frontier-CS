#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <bitset>

using namespace std;

string combine_balanced(const vector<string>& exprs, int l, int r, char op) {
    if (l == r) return exprs[l];
    int mid = (l + r) / 2;
    string left = combine_balanced(exprs, l, mid, op);
    string right = combine_balanced(exprs, mid + 1, r, op);
    return "(" + left + op + right + ")";
}

string build_and(const vector<int>& vars) {
    if (vars.size() == 1) {
        return string(1, 'a' + vars[0]);
    }
    vector<string> var_exprs;
    for (int idx : vars) {
        var_exprs.push_back(string(1, 'a' + idx));
    }
    return combine_balanced(var_exprs, 0, var_exprs.size() - 1, '&');
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    
    int T;
    cin >> T;
    while (T--) {
        int n;
        cin >> n;
        string s;
        cin >> s;
        int N = 1 << n;
        vector<bool> f(N, false);
        int ones = 0;
        for (int i = 0; i < N; ++i) {
            f[i] = (s[i] == '1');
            if (f[i]) ones++;
        }
        
        // Check monotonicity
        bool monotone = true;
        for (int i = 0; i < n && monotone; ++i) {
            int bit = 1 << i;
            for (int mask = 0; mask < N; ++mask) {
                if ((mask & bit) == 0) {
                    if (f[mask] && !f[mask | bit]) {
                        monotone = false;
                        break;
                    }
                }
            }
        }
        
        if (!monotone) {
            cout << "No\n";
            continue;
        }
        
        // Constant cases
        if (ones == 0) {
            cout << "Yes\nF\n";
            continue;
        }
        if (ones == N) {
            cout << "Yes\nT\n";
            continue;
        }
        
        // Collect all true masks
        vector<int> true_masks;
        for (int mask = 0; mask < N; ++mask) {
            if (f[mask]) true_masks.push_back(mask);
        }
        // Sort by number of ones (popcount)
        sort(true_masks.begin(), true_masks.end(),
             [](int a, int b) { return __builtin_popcount(a) < __builtin_popcount(b); });
        
        // Find minimal true points (prime implicants)
        vector<int> min_masks;
        for (int mask : true_masks) {
            bool is_minimal = true;
            for (int i = 0; i < n; ++i) {
                if (mask & (1 << i)) {
                    int sub = mask ^ (1 << i);
                    if (f[sub]) {
                        is_minimal = false;
                        break;
                    }
                }
            }
            if (is_minimal) {
                min_masks.push_back(mask);
            }
        }
        
        // Build AND-terms for each minimal mask
        vector<string> terms;
        for (int mask : min_masks) {
            vector<int> vars;
            for (int i = 0; i < n; ++i) {
                if (mask & (1 << i)) vars.push_back(i);
            }
            terms.push_back(build_and(vars));
        }
        
        // Combine all terms with balanced OR
        string expr;
        if (terms.size() == 1) {
            expr = terms[0];
        } else {
            expr = combine_balanced(terms, 0, terms.size() - 1, '|');
        }
        
        cout << "Yes\n" << expr << "\n";
    }
    
    return 0;
}