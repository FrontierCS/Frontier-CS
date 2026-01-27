#include <bits/stdc++.h>
using namespace std;

static string buildBalanced(const vector<string>& items, char op) {
    if (items.empty()) return "";
    function<string(int,int)> rec = [&](int l, int r)->string {
        if (r - l == 1) return items[l];
        int m = (l + r) / 2;
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

static string termFromMask(int mask, int n) {
    vector<string> vars;
    vars.reserve(n);
    for (int i = 0; i < n; ++i) {
        if (mask & (1<<i)) {
            string v;
            v.push_back(char('a' + i));
            vars.push_back(v);
        }
    }
    if (vars.empty()) return "T";
    if (vars.size() == 1) return vars[0];
    return buildBalanced(vars, '&');
}

static string clauseFromMask(int mask, int n) {
    vector<string> vars;
    vars.reserve(n);
    for (int i = 0; i < n; ++i) {
        if ((mask & (1<<i)) == 0) {
            string v;
            v.push_back(char('a' + i));
            vars.push_back(v);
        }
    }
    if (vars.empty()) return "F";
    if (vars.size() == 1) return vars[0];
    return buildBalanced(vars, '|');
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
        int N = 1 << n;
        // Monotonicity check
        bool mono = true;
        for (int i = 0; mono && i < n; ++i) {
            int bit = 1 << i;
            for (int mask = 0; mask < N; ++mask) {
                if ((mask & bit) == 0) {
                    if (s[mask] == '1' && s[mask | bit] == '0') {
                        mono = false;
                        break;
                    }
                }
            }
        }
        if (!mono) {
            cout << "No\n";
            continue;
        }
        // Constant checks
        bool all0 = true, all1 = true;
        for (char c : s) {
            if (c == '1') all0 = false;
            else all1 = false;
        }
        cout << "Yes\n";
        if (all0) {
            cout << "F\n";
            continue;
        }
        if (all1) {
            cout << "T\n";
            continue;
        }
        // Collect minimal true points and maximal false points
        vector<int> mins;
        vector<int> maxf;
        mins.reserve(N);
        maxf.reserve(N);
        for (int mask = 0; mask < N; ++mask) {
            if (s[mask] == '1') {
                bool minimal = true;
                if (mask == 0) {
                    // would have been all1 handled already
                    minimal = false;
                } else {
                    int m = mask;
                    while (m) {
                        int b = m & -m;
                        int j = __builtin_ctz(b);
                        if (s[mask ^ (1<<j)] == '1') { minimal = false; break; }
                        m ^= b;
                    }
                }
                if (minimal) mins.push_back(mask);
            } else {
                bool maximal = true;
                if (mask == (N-1)) {
                    // would have been all0 handled already
                    maximal = false;
                } else {
                    for (int i = 0; i < n; ++i) {
                        if ((mask & (1<<i)) == 0) {
                            if (s[mask | (1<<i)] == '0') { maximal = false; break; }
                        }
                    }
                }
                if (maximal) maxf.push_back(mask);
            }
        }
        // Compute operator counts
        long long dnf_ops = (long long)mins.size() - 1;
        for (int m : mins) dnf_ops += (__builtin_popcount((unsigned)m) - 1);
        long long cnf_ops = (long long)maxf.size() - 1;
        for (int m : maxf) cnf_ops += ((n - __builtin_popcount((unsigned)m)) - 1);
        // Build chosen expression
        string expr;
        if (dnf_ops <= cnf_ops) {
            vector<string> terms;
            terms.reserve(mins.size());
            for (int m : mins) terms.push_back(termFromMask(m, n));
            if (terms.size() == 1) expr = terms[0];
            else expr = buildBalanced(terms, '|');
        } else {
            vector<string> clauses;
            clauses.reserve(maxf.size());
            for (int m : maxf) clauses.push_back(clauseFromMask(m, n));
            if (clauses.size() == 1) expr = clauses[0];
            else expr = buildBalanced(clauses, '&');
        }
        cout << expr << "\n";
    }
    return 0;
}