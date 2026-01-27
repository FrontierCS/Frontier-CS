#include <bits/stdc++.h>
using namespace std;

string build_and(const vector<int>& vars, int l, int r) {
    if (r - l == 1) {
        char c = 'a' + vars[l];
        return string(1, c);
    }
    int m = (l + r) / 2;
    string left = build_and(vars, l, m);
    string right = build_and(vars, m, r);
    string res;
    res.reserve(left.size() + right.size() + 3);
    res.push_back('(');
    res += left;
    res.push_back('&');
    res += right;
    res.push_back(')');
    return res;
}

string build_or(const vector<string>& terms, int l, int r) {
    if (r - l == 1) return terms[l];
    int m = (l + r) / 2;
    string left = build_or(terms, l, m);
    string right = build_or(terms, m, r);
    string res;
    res.reserve(left.size() + right.size() + 3);
    res.push_back('(');
    res += left;
    res.push_back('|');
    res += right;
    res.push_back(')');
    return res;
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
        vector<uint8_t> f(N);
        bool has1 = false, has0 = false;
        for (int i = 0; i < N; ++i) {
            char c = s[i];
            f[i] = (c == '1');
            if (c == '1') has1 = true;
            else has0 = true;
        }

        bool ok = true;
        for (int i = 0; i < n && ok; ++i) {
            int bit = 1 << i;
            for (int mask = 0; mask < N; ++mask) {
                if (!(mask & bit)) {
                    if (f[mask] && !f[mask | bit]) {
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

        if (!has1) {
            cout << "F\n";
            continue;
        }
        if (!has0) {
            cout << "T\n";
            continue;
        }

        vector<int> mins;
        mins.reserve(N);
        for (int mask = 0; mask < N; ++mask) {
            if (!f[mask]) continue;
            bool isMin = true;
            for (int i = 0; i < n; ++i) {
                if (mask & (1 << i)) {
                    if (f[mask ^ (1 << i)]) {
                        isMin = false;
                        break;
                    }
                }
            }
            if (isMin) mins.push_back(mask);
        }

        vector<string> terms;
        terms.reserve(mins.size());
        for (int mask : mins) {
            vector<int> vars;
            vars.reserve(n);
            for (int i = 0; i < n; ++i) {
                if (mask & (1 << i)) vars.push_back(i);
            }
            if (vars.empty()) {
                terms.emplace_back("T");
            } else if (vars.size() == 1) {
                char c = 'a' + vars[0];
                terms.emplace_back(1, c);
            } else {
                terms.emplace_back(build_and(vars, 0, (int)vars.size()));
            }
        }

        string expr;
        if (terms.size() == 1) expr = terms[0];
        else expr = build_or(terms, 0, (int)terms.size());
        cout << expr << "\n";
    }
    return 0;
}