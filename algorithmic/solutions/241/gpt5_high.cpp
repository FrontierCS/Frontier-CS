#include <bits/stdc++.h>
using namespace std;

static inline int popcnt(unsigned x){ return __builtin_popcount(x); }

string joinBalanced(vector<string> items, char op) {
    if (items.empty()) return "";
    while (items.size() > 1) {
        vector<string> next;
        next.reserve((items.size()+1)/2);
        for (size_t i = 0; i < items.size(); i += 2) {
            if (i + 1 < items.size()) {
                string s;
                s.reserve(items[i].size() + items[i+1].size() + 3);
                s.push_back('(');
                s += items[i];
                s.push_back(op);
                s += items[i+1];
                s.push_back(')');
                next.push_back(move(s));
            } else {
                next.push_back(move(items[i]));
            }
        }
        items.swap(next);
    }
    return items[0];
}

string buildANDfromMask(unsigned mask, int n) {
    vector<string> vars;
    vars.reserve(popcnt(mask));
    for (int i = 0; i < n; ++i) {
        if (mask & (1u << i)) {
            char c = 'a' + i;
            string t(1, c);
            vars.push_back(move(t));
        }
    }
    if (vars.empty()) return "T";
    if (vars.size() == 1) return vars[0];
    return joinBalanced(vars, '&');
}

string buildORfromZerosMask(unsigned mask, int n) {
    vector<string> vars;
    vars.reserve(n - popcnt(mask));
    for (int i = 0; i < n; ++i) {
        if ((mask & (1u << i)) == 0u) {
            char c = 'a' + i;
            string t(1, c);
            vars.push_back(move(t));
        }
    }
    if (vars.empty()) return "F";
    if (vars.size() == 1) return vars[0];
    return joinBalanced(vars, '|');
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
        vector<char> val(M);
        bool all0 = true, all1 = true;
        for (int i = 0; i < M; ++i) {
            val[i] = (s[i] == '1');
            if (val[i]) all0 = false;
            else all1 = false;
        }

        bool monotone = true;
        for (int i = 0; monotone && i < n; ++i) {
            int bit = 1 << i;
            for (int j = 0; j < M; ++j) {
                if (j & bit) continue;
                if (val[j] > val[j | bit]) { monotone = false; break; }
            }
        }

        if (!monotone) {
            cout << "No\n";
            continue;
        }

        cout << "Yes\n";
        if (all1) {
            cout << "T\n";
            continue;
        }
        if (all0) {
            cout << "F\n";
            continue;
        }

        // Collect minimal 1s (for DNF) and maximal 0s (for CNF), and compute costs
        vector<unsigned> minOnes;
        long long costDNF = 0;
        for (int x = 0; x < M; ++x) {
            if (!val[x]) continue;
            bool minimal = true;
            unsigned ux = (unsigned)x;
            for (int i = 0; i < n; ++i) {
                if (ux & (1u << i)) {
                    if (val[x ^ (1 << i)]) { minimal = false; break; }
                }
            }
            if (minimal) {
                minOnes.push_back(ux);
                costDNF += popcnt(ux);
            }
        }
        if (!minOnes.empty()) costDNF -= 1;

        vector<unsigned> maxZeros;
        long long costCNF = 0;
        for (int x = 0; x < M; ++x) {
            if (val[x]) continue;
            bool maximal = true;
            unsigned ux = (unsigned)x;
            for (int i = 0; i < n; ++i) {
                if ((ux & (1u << i)) == 0u) {
                    if (!val[x | (1 << i)]) { maximal = false; break; }
                }
            }
            if (maximal) {
                maxZeros.push_back(ux);
                costCNF += (n - popcnt(ux));
            }
        }
        if (!maxZeros.empty()) costCNF -= 1;

        // Choose representation
        bool useDNF = (costDNF <= costCNF);

        if (useDNF) {
            vector<string> terms;
            terms.reserve(minOnes.size());
            for (unsigned m : minOnes) {
                terms.push_back(buildANDfromMask(m, n));
            }
            if (terms.empty()) {
                cout << "F\n";
            } else if (terms.size() == 1) {
                cout << terms[0] << "\n";
            } else {
                cout << joinBalanced(terms, '|') << "\n";
            }
        } else {
            vector<string> clauses;
            clauses.reserve(maxZeros.size());
            for (unsigned z : maxZeros) {
                clauses.push_back(buildORfromZerosMask(z, n));
            }
            if (clauses.empty()) {
                cout << "T\n";
            } else if (clauses.size() == 1) {
                cout << clauses[0] << "\n";
            } else {
                cout << joinBalanced(clauses, '&') << "\n";
            }
        }
    }
    return 0;
}