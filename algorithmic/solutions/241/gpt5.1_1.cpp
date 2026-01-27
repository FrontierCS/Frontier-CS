#include <bits/stdc++.h>
using namespace std;

string build_and_term_from_mask(int mask, int n) {
    vector<char> vars;
    for (int i = 0; i < n; ++i) {
        if (mask & (1 << i)) vars.push_back('a' + i);
    }
    if (vars.empty()) return "T";
    string expr;
    expr.push_back(vars[0]);
    for (size_t i = 1; i < vars.size(); ++i) {
        string tmp;
        tmp.reserve(expr.size() + 3 + 1);
        tmp.push_back('(');
        tmp += expr;
        tmp.push_back('&');
        tmp.push_back(vars[i]);
        tmp.push_back(')');
        expr.swap(tmp);
    }
    return expr;
}

string build_or_clause_from_mask(int mask, int n) {
    vector<char> vars;
    for (int i = 0; i < n; ++i) {
        if (!(mask & (1 << i))) vars.push_back('a' + i);
    }
    if (vars.empty()) return "F";
    string expr;
    expr.push_back(vars[0]);
    for (size_t i = 1; i < vars.size(); ++i) {
        string tmp;
        tmp.reserve(expr.size() + 3 + 1);
        tmp.push_back('(');
        tmp += expr;
        tmp.push_back('|');
        tmp.push_back(vars[i]);
        tmp.push_back(')');
        expr.swap(tmp);
    }
    return expr;
}

string combine_balanced(vector<string> vec, char op) {
    if (vec.empty()) return "";
    while (vec.size() > 1) {
        vector<string> next;
        next.reserve((vec.size() + 1) / 2);
        for (size_t i = 0; i < vec.size(); i += 2) {
            if (i + 1 == vec.size()) {
                next.push_back(std::move(vec[i]));
            } else {
                string &left = vec[i];
                string &right = vec[i + 1];
                string tmp;
                tmp.reserve(left.size() + right.size() + 3);
                tmp.push_back('(');
                tmp += left;
                tmp.push_back(op);
                tmp += right;
                tmp.push_back(')');
                next.push_back(std::move(tmp));
            }
        }
        vec.swap(next);
    }
    return vec[0];
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int T;
    if (!(cin >> T)) return 0;
    while (T--) {
        int n;
        string s;
        cin >> n >> s;
        int L = 1 << n;

        // Monotonicity check
        bool monotone = true;
        for (int mask = 0; mask < L && monotone; ++mask) {
            for (int i = 0; i < n; ++i) {
                if ((mask & (1 << i)) == 0) {
                    int up = mask | (1 << i);
                    if (s[mask] == '1' && s[up] == '0') {
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

        bool has1 = false, has0 = false;
        for (char c : s) {
            if (c == '1') has1 = true;
            else has0 = true;
        }

        if (!has1) {
            cout << "Yes\nF\n";
            continue;
        }
        if (!has0) {
            cout << "Yes\nT\n";
            continue;
        }

        vector<int> minOnes;
        vector<int> maxZeros;
        minOnes.reserve(L);
        maxZeros.reserve(L);

        for (int mask = 0; mask < L; ++mask) {
            if (s[mask] == '1') {
                bool minimal = true;
                int t = mask;
                while (t) {
                    int lsb = t & -t;
                    int prev = mask ^ lsb;
                    if (s[prev] == '1') {
                        minimal = false;
                        break;
                    }
                    t ^= lsb;
                }
                if (minimal) minOnes.push_back(mask);
            } else {
                bool maximal = true;
                for (int i = 0; i < n; ++i) {
                    if ((mask & (1 << i)) == 0) {
                        int nxt = mask | (1 << i);
                        if (s[nxt] == '0') {
                            maximal = false;
                            break;
                        }
                    }
                }
                if (maximal) maxZeros.push_back(mask);
            }
        }

        long long ops_dnf = 0;
        for (int mask : minOnes) {
            int pc = __builtin_popcount(mask);
            if (pc >= 2) ops_dnf += pc - 1;
        }
        if (minOnes.size() >= 2) ops_dnf += (long long)minOnes.size() - 1;

        long long ops_cnf = 0;
        for (int mask : maxZeros) {
            int pc = __builtin_popcount(mask);
            int clauseVars = n - pc;
            if (clauseVars >= 2) ops_cnf += clauseVars - 1;
        }
        if (maxZeros.size() >= 2) ops_cnf += (long long)maxZeros.size() - 1;

        bool useDNF = (ops_dnf <= ops_cnf);

        cout << "Yes\n";
        if (useDNF) {
            vector<string> terms;
            terms.reserve(minOnes.size());
            for (int mask : minOnes) {
                terms.push_back(build_and_term_from_mask(mask, n));
            }
            string expr = combine_balanced(terms, '|');
            cout << expr << "\n";
        } else {
            vector<string> clauses;
            clauses.reserve(maxZeros.size());
            for (int mask : maxZeros) {
                clauses.push_back(build_or_clause_from_mask(mask, n));
            }
            string expr = combine_balanced(clauses, '&');
            cout << expr << "\n";
        }
    }
    return 0;
}