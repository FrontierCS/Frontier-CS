#include <iostream>
#include <vector>
#include <map>
#include <algorithm>
#include <string>
#include <cassert>
#include <climits>
#include <bitset>

using namespace std;

string var_name(int i) {
    return string(1, 'a' + i);
}

// Build conjunction expression for a given minterm mask (non-empty)
string conj_expr(int mask, int n) {
    vector<int> vars;
    for (int i = 0; i < n; ++i) {
        if (mask & (1 << i)) vars.push_back(i);
    }
    string res = var_name(vars[0]);
    for (size_t i = 1; i < vars.size(); ++i) {
        res = "(" + res + "&" + var_name(vars[i]) + ")";
    }
    return res;
}

// Build DNF expression directly from minterms
string build_dnf(const vector<int>& minterms, int n) {
    vector<string> terms;
    for (int m : minterms) {
        terms.push_back(conj_expr(m, n));
    }
    string res = terms[0];
    for (size_t i = 1; i < terms.size(); ++i) {
        res = "(" + res + "|" + terms[i] + ")";
    }
    return res;
}

map<vector<int>, pair<string, int>> memo;

pair<string, int> solve_set(vector<int> S, int n) {
    if (S.empty()) return {"F", 0};
    // Check if S contains 0 (empty minterm)
    for (int m : S) if (m == 0) return {"T", 0};
    if (S.size() == 1) {
        int m = S[0];
        // m != 0
        string expr = conj_expr(m, n);
        int op_cnt = __builtin_popcount(m) - 1;
        return {expr, op_cnt};
    }
    // Sort for canonical key
    sort(S.begin(), S.end());
    auto it = memo.find(S);
    if (it != memo.end()) return it->second;

    // Compute union of variables present
    int union_mask = 0;
    for (int m : S) union_mask |= m;

    // Choose variables to try: if S is small, try all; otherwise greedy pick most frequent
    vector<int> vars_to_try;
    if (S.size() <= 10) {
        for (int i = 0; i < n; ++i) {
            if (union_mask & (1 << i)) vars_to_try.push_back(i);
        }
    } else {
        vector<int> freq(n, 0);
        for (int m : S) {
            for (int i = 0; i < n; ++i) if (m & (1 << i)) freq[i]++;
        }
        int best_var = -1, best_freq = -1;
        for (int i = 0; i < n; ++i) {
            if (freq[i] > best_freq) {
                best_freq = freq[i];
                best_var = i;
            }
        }
        vars_to_try.push_back(best_var);
    }

    int best_cost = INT_MAX;
    string best_expr;

    for (int x : vars_to_try) {
        vector<int> S0, S1;
        for (int m : S) {
            if (m & (1 << x)) S1.push_back(m);
            else S0.push_back(m);
        }
        // Remove duplicates (should not happen, but safe)
        sort(S0.begin(), S0.end());
        S0.erase(unique(S0.begin(), S0.end()), S0.end());
        sort(S1.begin(), S1.end());
        S1.erase(unique(S1.begin(), S1.end()), S1.end());

        // Build S1' by removing x from each minterm in S1
        vector<int> S1p;
        bool empty_present = false;
        for (int m : S1) {
            int m1 = m & ~(1 << x);
            if (m1 == 0) empty_present = true;
            else S1p.push_back(m1);
        }
        sort(S1p.begin(), S1p.end());
        S1p.erase(unique(S1p.begin(), S1p.end()), S1p.end());

        auto [f0, c0] = solve_set(S0, n);
        string f1;
        int c1;
        if (empty_present) {
            f1 = "T";
            c1 = 0;
        } else {
            auto res = solve_set(S1p, n);
            f1 = res.first;
            c1 = res.second;
        }

        string expr;
        int cost;
        if (f1 == "T" && f0 == "F") {
            expr = var_name(x);
            cost = 0;
        } else if (f1 == "T") {
            expr = "(" + var_name(x) + "|" + f0 + ")";
            cost = 1 + c0;
        } else if (f0 == "F") {
            expr = "(" + var_name(x) + "&" + f1 + ")";
            cost = 1 + c1;
        } else {
            expr = "((" + var_name(x) + "&" + f1 + ")|" + f0 + ")";
            cost = 2 + c0 + c1;
        }
        if (cost < best_cost) {
            best_cost = cost;
            best_expr = expr;
        }
    }
    memo[S] = {best_expr, best_cost};
    return {best_expr, best_cost};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    cin >> T;
    while (T--) {
        int n;
        cin >> n;
        string s;
        cin >> s;
        int N = 1 << n;
        assert((int)s.size() == N);

        // ----- Monotonicity check -----
        bool monotone = true;
        for (int i = 0; i < N; ++i) {
            if (s[i] == '1') {
                for (int j = 0; j < n; ++j) {
                    if (!(i & (1 << j))) {
                        int v = i | (1 << j);
                        if (s[v] == '0') {
                            monotone = false;
                            break;
                        }
                    }
                }
                if (!monotone) break;
            }
        }
        if (!monotone) {
            cout << "No\n";
            continue;
        }

        // ----- Compute minterms -----
        vector<vector<int>> by_popcount(n + 1);
        for (int i = 0; i < N; ++i) {
            if (s[i] == '1') {
                int pc = __builtin_popcount(i);
                by_popcount[pc].push_back(i);
            }
        }
        vector<int> minterms;
        for (int w = 0; w <= n; ++w) {
            for (int i : by_popcount[w]) {
                bool minimal = true;
                for (int j = 0; j < n; ++j) {
                    if (i & (1 << j)) {
                        int sub = i ^ (1 << j);
                        if (s[sub] == '1') {
                            minimal = false;
                            break;
                        }
                    }
                }
                if (minimal) minterms.push_back(i);
            }
        }

        // ----- Handle constant functions -----
        if (minterms.empty()) {  // all zeros
            cout << "Yes\nF\n";
            continue;
        }
        bool has_empty = false;
        for (int m : minterms) {
            if (m == 0) {
                has_empty = true;
                break;
            }
        }
        if (has_empty) {  // constant true
            cout << "Yes\nT\n";
            continue;
        }

        // ----- Build expression -----
        string expr;
        if (minterms.size() > 100) {
            expr = build_dnf(minterms, n);
        } else {
            sort(minterms.begin(), minterms.end());
            memo.clear();
            expr = solve_set(minterms, n).first;
        }
        cout << "Yes\n" << expr << "\n";
    }
    return 0;
}