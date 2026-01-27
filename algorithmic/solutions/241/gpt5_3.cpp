#include <bits/stdc++.h>
using namespace std;

static string joinBalanced(const vector<string>& items, char op) {
    if (items.empty()) return "";
    function<string(int,int)> rec = [&](int l, int r) -> string {
        if (r - l == 1) return items[l];
        int m = (l + r) >> 1;
        string L = rec(l, m);
        string R = rec(m, r);
        string res;
        res.reserve(L.size() + R.size() + 3);
        res.push_back('(');
        res += L;
        res.push_back(op);
        res += R;
        res.push_back(')');
        return res;
    };
    return rec(0, (int)items.size());
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
        int m = 1 << n;
        if ((int)s.size() != m) {
            cout << "No\n";
            continue;
        }
        // Check monotonicity: for each bit j, for all masks with bit j = 0, f(mask) <= f(mask | (1<<j))
        bool ok = true;
        for (int j = 0; j < n && ok; ++j) {
            for (int mask = 0; mask < m; ++mask) {
                if (((mask >> j) & 1) == 0) {
                    if (s[mask] == '1' && s[mask | (1 << j)] == '0') {
                        ok = false;
                        break;
                    }
                }
            }
        }
        if (!ok) {
            cout << "No\n";
            continue;
        }
        cout << "Yes\n";
        // Precompute var symbols
        vector<string> varSym(n);
        for (int i = 0; i < n; ++i) varSym[i] = string(1, char('a' + i));

        // DNF: minimal true points
        vector<int> minTrue;
        for (int mask = 0; mask < m; ++mask) if (s[mask] == '1') {
            bool minimal = true;
            int t = mask;
            while (t) {
                int lsb = t & -t;
                if (s[mask ^ lsb] == '1') { minimal = false; break; }
                t ^= lsb;
            }
            if (minimal) minTrue.push_back(mask);
        }
        // CNF: maximal false points
        vector<int> maxFalse;
        for (int mask = 0; mask < m; ++mask) if (s[mask] == '0') {
            bool maximal = true;
            for (int j = 0; j < n; ++j) if (((mask >> j) & 1) == 0) {
                if (s[mask | (1 << j)] == '0') { maximal = false; break; }
            }
            if (maximal) maxFalse.push_back(mask);
        }

        // Build DNF expression and op count
        string exprDNF;
        long long opsDNF = 0;
        if (!minTrue.empty() && minTrue.size() == 1 && minTrue[0] == 0) {
            exprDNF = "T";
            opsDNF = 0;
        } else if (minTrue.empty()) {
            exprDNF = "F";
            opsDNF = 0;
        } else {
            vector<string> terms;
            terms.reserve(minTrue.size());
            for (int mask : minTrue) {
                vector<string> vars;
                vars.reserve(__builtin_popcount((unsigned)mask));
                for (int i = 0; i < n; ++i) if ((mask >> i) & 1) vars.push_back(varSym[i]);
                if (vars.size() == 1) {
                    terms.push_back(vars[0]);
                } else {
                    terms.push_back(joinBalanced(vars, '&'));
                }
                if (!vars.empty()) opsDNF += (int)vars.size() - 1;
            }
            if (terms.size() == 1) {
                exprDNF = terms[0];
            } else {
                exprDNF = joinBalanced(terms, '|');
                opsDNF += (int)terms.size() - 1;
            }
        }

        // Build CNF expression and op count
        string exprCNF;
        long long opsCNF = 0;
        bool hasAllOnesMaxFalse = false;
        for (int mask : maxFalse) {
            if (mask == (m - 1)) { hasAllOnesMaxFalse = true; break; }
        }
        if (hasAllOnesMaxFalse) {
            exprCNF = "F";
            opsCNF = 0;
        } else if (maxFalse.empty()) {
            exprCNF = "T";
            opsCNF = 0;
        } else {
            vector<string> clauses;
            clauses.reserve(maxFalse.size());
            for (int mask : maxFalse) {
                vector<string> vars;
                vars.reserve(n - __builtin_popcount((unsigned)mask));
                for (int i = 0; i < n; ++i) if (((mask >> i) & 1) == 0) vars.push_back(varSym[i]);
                if (vars.empty()) {
                    // Should not happen as we handled all-ones max false earlier
                    exprCNF = "F";
                    opsCNF = 0;
                    clauses.clear();
                    break;
                }
                if (vars.size() == 1) clauses.push_back(vars[0]);
                else clauses.push_back(joinBalanced(vars, '|'));
                opsCNF += (int)vars.size() - 1;
            }
            if (!exprCNF.empty() && exprCNF == "F") {
                // already set
            } else if (clauses.size() == 1) {
                exprCNF = clauses[0];
            } else {
                exprCNF = joinBalanced(clauses, '&');
                opsCNF += (int)clauses.size() - 1;
            }
        }

        // Choose the better one (fewer binary operators). If tie, choose shorter expression.
        string ans;
        if (opsDNF < opsCNF) ans = exprDNF;
        else if (opsCNF < opsDNF) ans = exprCNF;
        else {
            if (exprDNF.size() <= exprCNF.size()) ans = exprDNF;
            else ans = exprCNF;
        }

        cout << ans << "\n";
    }
    return 0;
}