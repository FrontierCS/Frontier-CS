#include <bits/stdc++.h>
using namespace std;

static string combine(char op, const vector<string>& parts, int l, int r) {
    if (r - l == 1) return parts[l];
    int m = l + (r - l) / 2;
    string left = combine(op, parts, l, m);
    string right = combine(op, parts, m, r);
    string res;
    res.reserve(left.size() + right.size() + 3);
    res.push_back('(');
    res += left;
    res.push_back(op);
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
        bool ok = true;
        // Check monotonicity: for any mask and bit i not set, s[mask] <= s[mask | (1<<i)]
        for (int mask = 0; ok && mask < N; ++mask) {
            if (s[mask] == '1') {
                int inv = (~mask) & (N - 1);
                int tmp = inv;
                while (tmp) {
                    int b = tmp & -tmp;
                    if (s[mask | b] == '0') { ok = false; break; }
                    tmp ^= b;
                }
            }
        }
        if (!ok) {
            cout << "No\n";
            continue;
        }
        // Find minimal true points
        vector<int> mins;
        for (int mask = 0; mask < N; ++mask) {
            if (s[mask] != '1') continue;
            bool minimal = true;
            int tmp = mask;
            while (tmp) {
                int b = tmp & -tmp;
                if (s[mask ^ b] == '1') { minimal = false; break; }
                tmp ^= b;
            }
            if (minimal) mins.push_back(mask);
        }
        cout << "Yes\n";
        if (mins.empty()) {
            cout << "F\n";
            continue;
        }
        // Build terms
        vector<string> terms;
        terms.reserve(mins.size());
        for (int m : mins) {
            if (m == 0) {
                terms.push_back("T");
                continue;
            }
            vector<string> vars;
            for (int i = 0; i < n; ++i) {
                if (m & (1 << i)) {
                    char c = 'a' + i;
                    vars.emplace_back(string(1, c));
                }
            }
            if (vars.size() == 1) {
                terms.push_back(vars[0]);
            } else {
                terms.push_back(combine('&', vars, 0, (int)vars.size()));
            }
        }
        string expr;
        if (terms.size() == 1) {
            expr = terms[0];
        } else {
            expr = combine('|', terms, 0, (int)terms.size());
        }
        cout << expr << "\n";
    }
    return 0;
}