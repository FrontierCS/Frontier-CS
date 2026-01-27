#include <bits/stdc++.h>
using namespace std;

string build_range(const vector<string> &arr, int l, int r, char op) {
    int len = r - l;
    if (len == 1) return arr[l];
    int mid = (l + r) / 2;
    string left = build_range(arr, l, mid, op);
    string right = build_range(arr, mid, r, op);
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
        cin >> n >> s;
        int M = 1 << n;

        bool mono = true;
        for (int mask = 0; mask < M && mono; ++mask) {
            char val = s[mask];
            for (int i = 0; i < n; ++i) {
                if (mask & (1 << i)) {
                    int prev = mask ^ (1 << i);
                    if (s[prev] == '1' && val == '0') {
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

        cout << "Yes\n";

        bool all0 = true, all1 = true;
        for (char c : s) {
            if (c == '1') all0 = false;
            else all1 = false;
        }

        if (all0) {
            cout << "F\n";
            continue;
        }
        if (all1) {
            cout << "T\n";
            continue;
        }

        vector<int> mins;
        mins.reserve(M);
        for (int mask = 0; mask < M; ++mask) {
            if (s[mask] == '1') {
                bool minimal = true;
                for (int i = 0; i < n; ++i) {
                    if (mask & (1 << i)) {
                        int prev = mask ^ (1 << i);
                        if (s[prev] == '1') {
                            minimal = false;
                            break;
                        }
                    }
                }
                if (minimal) mins.push_back(mask);
            }
        }

        vector<string> terms;
        terms.reserve(mins.size());

        for (int mask : mins) {
            vector<string> vars;
            vars.reserve(n);
            for (int i = 0; i < n; ++i) {
                if (mask & (1 << i)) {
                    string v(1, char('a' + i));
                    vars.push_back(std::move(v));
                }
            }
            if (vars.empty()) {
                terms.emplace_back("T");
            } else if (vars.size() == 1) {
                terms.push_back(vars[0]);
            } else {
                string conj = build_range(vars, 0, (int)vars.size(), '&');
                terms.push_back(std::move(conj));
            }
        }

        string expr;
        if (terms.size() == 1) {
            expr = std::move(terms[0]);
        } else {
            expr = build_range(terms, 0, (int)terms.size(), '|');
        }

        cout << expr << '\n';
    }

    return 0;
}