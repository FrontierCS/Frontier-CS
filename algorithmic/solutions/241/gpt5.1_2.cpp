#include <bits/stdc++.h>
using namespace std;

string combineOp(const vector<string>& v, char op, int l, int r) {
    if (r - l == 1) return v[l];
    int m = (l + r) / 2;
    string L = combineOp(v, op, l, m);
    string R = combineOp(v, op, m, r);
    string res;
    res.reserve(L.size() + R.size() + 3);
    res.push_back('(');
    res += L;
    res.push_back(op);
    res += R;
    res.push_back(')');
    return res;
}

string buildOp(const vector<string>& v, char op) {
    if (v.empty()) return "";
    if (v.size() == 1) return v[0];
    return combineOp(v, op, 0, (int)v.size());
}

string buildAndMask(int mask, int n) {
    vector<string> atoms;
    atoms.reserve(n);
    for (int i = 0; i < n; i++) {
        if (mask & (1 << i)) {
            string var(1, char('a' + i));
            atoms.push_back(var);
        }
    }
    if (atoms.empty()) {
        // Should not occur in our usage (mask == 0 handled separately)
        return "T";
    }
    return buildOp(atoms, '&');
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
        int L = 1 << n;
        vector<char> f(L);
        int ones = 0;
        for (int i = 0; i < L; i++) {
            f[i] = s[i] - '0';
            if (f[i]) ones++;
        }

        bool ok = true;
        if (n > 0) {
            for (int mask = 0; mask < L && ok; mask++) {
                if (!f[mask]) continue;
                for (int i = 0; i < n; i++) {
                    if ((mask & (1 << i)) == 0) {
                        int up = mask | (1 << i);
                        if (!f[up]) {
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
        if (ones == 0) {
            cout << "F\n";
            continue;
        }
        if (f[0]) {
            cout << "T\n";
            continue;
        }

        vector<int> mins;
        mins.reserve(ones);
        for (int mask = 0; mask < L; mask++) {
            if (!f[mask]) continue;
            bool minimal = true;
            for (int i = 0; i < n; i++) {
                if (mask & (1 << i)) {
                    int pre = mask ^ (1 << i);
                    if (f[pre]) {
                        minimal = false;
                        break;
                    }
                }
            }
            if (minimal) mins.push_back(mask);
        }

        vector<string> terms;
        terms.reserve(mins.size());
        for (int m : mins) {
            terms.push_back(buildAndMask(m, n));
        }

        string expr = buildOp(terms, '|');
        cout << expr << "\n";
    }
    return 0;
}