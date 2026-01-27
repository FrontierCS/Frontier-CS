#include <bits/stdc++.h>
using namespace std;

static string combineRange(const vector<string>& arr, int l, int r, char op) {
    if (r - l == 1) return arr[l];
    int m = (l + r) >> 1;
    string left = combineRange(arr, l, m, op);
    string right = combineRange(arr, m, r, op);
    string res;
    res.reserve(left.size() + right.size() + 3);
    res.push_back('(');
    res += left;
    res.push_back(op);
    res += right;
    res.push_back(')');
    return res;
}

static string combineBalanced(const vector<string>& parts, char op) {
    if (parts.empty()) return ""; // should not happen
    if (parts.size() == 1) return parts[0];
    return combineRange(parts, 0, (int)parts.size(), op);
}

static string conjFromMask(int mask, int n) {
    vector<string> vars;
    for (int j = 0; j < n; ++j) {
        if (mask & (1 << j)) {
            string v(1, char('a' + j));
            vars.push_back(v);
        }
    }
    if (vars.empty()) return "T"; // only for the constant True case
    if (vars.size() == 1) return vars[0];
    return combineBalanced(vars, '&');
}

static string clauseFromZeroIndex(int idx, int n) {
    vector<string> vars;
    for (int j = 0; j < n; ++j) {
        if (((idx >> j) & 1) == 0) {
            string v(1, char('a' + j));
            vars.push_back(v);
        }
    }
    if (vars.empty()) return "F"; // only for the constant False case
    if (vars.size() == 1) return vars[0];
    return combineBalanced(vars, '|');
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        string s;
        cin >> n;
        cin >> s;
        int M = 1 << n;
        bool ok = true;
        // Monotonicity check: for each i, for each bit j=0 in i, s[i] <= s[i | (1<<j)]
        for (int i = 0; i < M && ok; ++i) {
            for (int j = 0; j < n; ++j) {
                if ((i & (1 << j)) == 0) {
                    if (s[i] > s[i | (1 << j)]) { ok = false; break; }
                }
            }
        }
        if (!ok) {
            cout << "No\n";
            continue;
        }
        cout << "Yes\n";
        // Constants quick check
        if (s[0] == '1') { // all ones due to monotonicity
            cout << "T\n";
            continue;
        }
        if (s[M - 1] == '0') { // all zeros due to monotonicity
            cout << "F\n";
            continue;
        }
        // Collect minimal ones and maximal zeros
        vector<int> minOnes;
        vector<int> maxZeros;
        long long dnfSumK = 0;
        long long cnfSumL = 0;
        for (int i = 0; i < M; ++i) {
            if (s[i] == '1') {
                bool minimal = true;
                int x = i;
                while (x) {
                    int j = __builtin_ctz(x);
                    if (s[i ^ (1 << j)] == '1') { minimal = false; break; }
                    x &= x - 1;
                }
                if (minimal) {
                    minOnes.push_back(i);
                    dnfSumK += __builtin_popcount(i);
                }
            } else { // s[i]=='0'
                bool maximal = true;
                for (int j = 0; j < n; ++j) {
                    if ((i & (1 << j)) == 0) {
                        if (s[i | (1 << j)] == '0') { maximal = false; break; }
                    }
                }
                if (maximal) {
                    maxZeros.push_back(i);
                    cnfSumL += (n - __builtin_popcount(i));
                }
            }
        }
        // Compute operator counts
        const long long INF = (1LL<<60);
        long long dnfCost = INF, cnfCost = INF;
        if (!minOnes.empty()) dnfCost = dnfSumK - 1;
        if (!maxZeros.empty()) cnfCost = cnfSumL - 1;
        // Decide which to build
        bool useDNF = true;
        if (dnfCost == INF && cnfCost != INF) useDNF = false;
        else if (cnfCost == INF && dnfCost != INF) useDNF = true;
        else if (dnfCost != INF && cnfCost != INF) {
            if (cnfCost < dnfCost) useDNF = false;
            else useDNF = true;
        }
        // Build chosen expression with balanced parentheses
        if (useDNF) {
            // If somehow empty, fallback constants already handled
            vector<string> terms;
            terms.reserve(minOnes.size());
            for (int idx : minOnes) {
                terms.push_back(conjFromMask(idx, n));
            }
            string expr = combineBalanced(terms, '|');
            cout << expr << "\n";
        } else {
            vector<string> clauses;
            clauses.reserve(maxZeros.size());
            for (int idx : maxZeros) {
                clauses.push_back(clauseFromZeroIndex(idx, n));
            }
            string expr = combineBalanced(clauses, '&');
            cout << expr << "\n";
        }
    }
    return 0;
}