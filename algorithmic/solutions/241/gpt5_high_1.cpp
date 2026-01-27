#include <bits/stdc++.h>
using namespace std;

static inline int popcount(int x){ return __builtin_popcount((unsigned)x); }

string combineBalanced(vector<string> items, char op) {
    if (items.empty()) return "";
    if (items.size() == 1) return items[0];
    vector<string> cur = move(items);
    while (cur.size() > 1) {
        vector<string> nxt;
        nxt.reserve((cur.size() + 1) / 2);
        for (size_t i = 0; i < cur.size(); i += 2) {
            if (i + 1 < cur.size()) {
                string t;
                t.reserve(cur[i].size() + cur[i+1].size() + 3);
                t.push_back('(');
                t += cur[i];
                t.push_back(op);
                t += cur[i+1];
                t.push_back(')');
                nxt.push_back(move(t));
            } else {
                nxt.push_back(move(cur[i]));
            }
        }
        cur.swap(nxt);
    }
    return cur[0];
}

string buildANDMask(int n, int mask) {
    vector<string> vars;
    vars.reserve(popcount(mask));
    for (int i = 0; i < n; ++i) if (mask & (1<<i)) {
        string v(1, char('a' + i));
        vars.push_back(move(v));
    }
    if (vars.empty()) return "T";
    if (vars.size() == 1) return vars[0];
    return combineBalanced(move(vars), '&');
}

string buildORMaskZeros(int n, int mask) {
    vector<string> vars;
    vars.reserve(n - popcount(mask));
    for (int i = 0; i < n; ++i) if ((mask & (1<<i)) == 0) {
        string v(1, char('a' + i));
        vars.push_back(move(v));
    }
    if (vars.empty()) return "F";
    if (vars.size() == 1) return vars[0];
    return combineBalanced(move(vars), '|');
}

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    if(!(cin >> T)) return 0;
    while (T--) {
        int n;
        string s;
        cin >> n;
        cin >> s;
        int N = 1 << n;
        bool ok = true;
        for (int mask = 0; mask < N && ok; ++mask) {
            if (s[mask] == '1') {
                for (int i = 0; i < n; ++i) if ((mask & (1<<i)) == 0) {
                    if (s[mask | (1<<i)] == '0') { ok = false; break; }
                }
            }
        }
        if (!ok) {
            cout << "No\n";
            continue;
        }
        cout << "Yes\n";
        bool all0 = true, all1 = true;
        for (char c : s) { if (c == '1') all0 = false; if (c == '0') all1 = false; }
        if (all1) { cout << "T\n"; continue; }
        if (all0) { cout << "F\n"; continue; }

        // Compute minimal ones and maximal zeros
        vector<int> minOnes;
        vector<int> maxZeros;
        minOnes.reserve(N);
        maxZeros.reserve(N);
        for (int mask = 0; mask < N; ++mask) {
            if (s[mask] == '1') {
                bool minimal = true;
                int mm = mask;
                while (mm) {
                    int i = __builtin_ctz(mm);
                    mm &= mm - 1;
                    if (s[mask ^ (1<<i)] == '1') { minimal = false; break; }
                }
                if (minimal) minOnes.push_back(mask);
            } else {
                bool maximal = true;
                for (int i = 0; i < n; ++i) if ((mask & (1<<i)) == 0) {
                    if (s[mask | (1<<i)] == '0') { maximal = false; break; }
                }
                if (maximal) maxZeros.push_back(mask);
            }
        }

        // Compute operator counts
        long long opsDNF = 0, opsCNF = 0;
        if (!minOnes.empty()) {
            long long sumAND = 0;
            for (int m : minOnes) {
                int k = popcount(m);
                if (k >= 2) sumAND += (k - 1);
            }
            long long orOps = (minOnes.size() >= 2) ? (long long)minOnes.size() - 1 : 0;
            opsDNF = sumAND + orOps;
        } else {
            opsDNF = (long long)1e18; // impossible
        }
        if (!maxZeros.empty()) {
            long long sumOR = 0;
            for (int m : maxZeros) {
                int k = n - popcount(m);
                if (k >= 2) sumOR += (k - 1);
            }
            long long andOps = (maxZeros.size() >= 2) ? (long long)maxZeros.size() - 1 : 0;
            opsCNF = sumOR + andOps;
        } else {
            opsCNF = (long long)1e18; // impossible
        }

        // Build the smaller one
        if (opsDNF <= opsCNF) {
            vector<string> terms;
            terms.reserve(minOnes.size());
            for (int m : minOnes) {
                terms.push_back(buildANDMask(n, m));
            }
            string expr = combineBalanced(move(terms), '|');
            cout << expr << "\n";
        } else {
            vector<string> clauses;
            clauses.reserve(maxZeros.size());
            for (int m : maxZeros) {
                clauses.push_back(buildORMaskZeros(n, m));
            }
            string expr = combineBalanced(move(clauses), '&');
            cout << expr << "\n";
        }
    }
    return 0;
}