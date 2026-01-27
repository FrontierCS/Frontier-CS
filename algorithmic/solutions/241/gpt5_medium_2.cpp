#include <bits/stdc++.h>
using namespace std;

static inline void print_and_range_vars(const vector<int>& vars, int l, int r, ostream& out) {
    if (r - l == 1) {
        out.put(char('a' + vars[l]));
    } else {
        int m = (l + r) >> 1;
        out.put('(');
        print_and_range_vars(vars, l, m, out);
        out.put('&');
        print_and_range_vars(vars, m, r, out);
        out.put(')');
    }
}

static inline void print_or_range_vars(const vector<int>& vars, int l, int r, ostream& out) {
    if (r - l == 1) {
        out.put(char('a' + vars[l]));
    } else {
        int m = (l + r) >> 1;
        out.put('(');
        print_or_range_vars(vars, l, m, out);
        out.put('|');
        print_or_range_vars(vars, m, r, out);
        out.put(')');
    }
}

static inline void print_dnf_terms_range(const vector<vector<int>>& terms, int l, int r, ostream& out) {
    if (r - l == 1) {
        const auto& v = terms[l];
        if (v.size() == 1) {
            out.put(char('a' + v[0]));
        } else {
            print_and_range_vars(v, 0, (int)v.size(), out);
        }
    } else {
        int m = (l + r) >> 1;
        out.put('(');
        print_dnf_terms_range(terms, l, m, out);
        out.put('|');
        print_dnf_terms_range(terms, m, r, out);
        out.put(')');
    }
}

static inline void print_cnf_clauses_range(const vector<vector<int>>& clauses, int l, int r, ostream& out) {
    if (r - l == 1) {
        const auto& v = clauses[l];
        if (v.size() == 1) {
            out.put(char('a' + v[0]));
        } else {
            print_or_range_vars(v, 0, (int)v.size(), out);
        }
    } else {
        int m = (l + r) >> 1;
        out.put('(');
        print_cnf_clauses_range(clauses, l, m, out);
        out.put('&');
        print_cnf_clauses_range(clauses, m, r, out);
        out.put(')');
    }
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
        bool ok = true;
        // Monotonicity check: for each mask, for each i with bit i = 0, f[mask] <= f[mask | (1<<i)]
        for (int m = 0; m < N && ok; ++m) {
            if (s[m] == '1') {
                for (int i = 0; i < n; ++i) {
                    if (((m >> i) & 1) == 0) {
                        if (s[m | (1 << i)] == '0') {
                            ok = false;
                            break;
                        }
                    }
                }
            }
        }
        if (!ok) {
            cout << "No\n";
            continue;
        }
        cout << "Yes\n";
        if (s[0] == '1') {
            cout << "T\n";
            continue;
        }
        if (s[N - 1] == '0') {
            cout << "F\n";
            continue;
        }
        // Build minimal true points for DNF
        vector<vector<int>> dnf_terms;
        dnf_terms.reserve(N);
        for (int m = 1; m < N; ++m) {
            if (s[m] == '1') {
                bool minimal = true;
                int mm = m;
                while (mm) {
                    int i = __builtin_ctz(mm);
                    mm &= (mm - 1);
                    if (s[m ^ (1 << i)] == '1') { minimal = false; break; }
                }
                if (minimal) {
                    vector<int> vars;
                    vars.reserve(__builtin_popcount(m));
                    for (int i = 0; i < n; ++i) if ((m >> i) & 1) vars.push_back(i);
                    dnf_terms.push_back(move(vars));
                }
            }
        }
        long long dnf_and = 0, dnf_or = 0;
        for (auto &v : dnf_terms) if ((int)v.size() >= 2) dnf_and += (int)v.size() - 1;
        if ((int)dnf_terms.size() >= 2) dnf_or = (int)dnf_terms.size() - 1;
        long long dnf_ops = dnf_and + dnf_or;

        // Build maximal false points for CNF
        vector<vector<int>> cnf_clauses;
        cnf_clauses.reserve(N);
        for (int m = 0; m < N - 1; ++m) {
            if (s[m] == '0') {
                bool maximal = true;
                for (int i = 0; i < n; ++i) {
                    if (((m >> i) & 1) == 0) {
                        if (s[m | (1 << i)] == '0') { maximal = false; break; }
                    }
                }
                if (maximal) {
                    vector<int> vars;
                    vars.reserve(n - __builtin_popcount(m));
                    for (int i = 0; i < n; ++i) if (((m >> i) & 1) == 0) vars.push_back(i);
                    cnf_clauses.push_back(move(vars));
                }
            }
        }
        long long cnf_or = 0, cnf_and = 0;
        for (auto &v : cnf_clauses) if ((int)v.size() >= 2) cnf_or += (int)v.size() - 1;
        if ((int)cnf_clauses.size() >= 2) cnf_and = (int)cnf_clauses.size() - 1;
        long long cnf_ops = cnf_or + cnf_and;

        if (cnf_ops < dnf_ops) {
            // print CNF
            if (cnf_clauses.size() == 1) {
                const auto& v = cnf_clauses[0];
                if (v.size() == 1) {
                    cout.put(char('a' + v[0]));
                } else {
                    print_or_range_vars(v, 0, (int)v.size(), cout);
                }
            } else {
                print_cnf_clauses_range(cnf_clauses, 0, (int)cnf_clauses.size(), cout);
            }
            cout << "\n";
        } else {
            // print DNF
            if (dnf_terms.size() == 1) {
                const auto& v = dnf_terms[0];
                if (v.size() == 1) {
                    cout.put(char('a' + v[0]));
                } else {
                    print_and_range_vars(v, 0, (int)v.size(), cout);
                }
            } else {
                print_dnf_terms_range(dnf_terms, 0, (int)dnf_terms.size(), cout);
            }
            cout << "\n";
        }
    }
    return 0;
}