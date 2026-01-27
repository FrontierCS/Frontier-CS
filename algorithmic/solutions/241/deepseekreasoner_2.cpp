#include <bits/stdc++.h>
using namespace std;

string build_and(const vector<int>& vars) {
    if (vars.size() == 1) {
        return string(1, 'a' + vars[0]);
    }
    int mid = vars.size() / 2;
    vector<int> left(vars.begin(), vars.begin() + mid);
    vector<int> right(vars.begin() + mid, vars.end());
    string left_expr = build_and(left);
    string right_expr = build_and(right);
    return "(" + left_expr + "&" + right_expr + ")";
}

string build_or(const vector<string>& exprs) {
    if (exprs.size() == 1) {
        return exprs[0];
    }
    int mid = exprs.size() / 2;
    vector<string> left(exprs.begin(), exprs.begin() + mid);
    vector<string> right(exprs.begin() + mid, exprs.end());
    string left_expr = build_or(left);
    string right_expr = build_or(right);
    return "(" + left_expr + "|" + right_expr + ")";
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    int T;
    cin >> T;
    while (T--) {
        int n;
        cin >> n;
        string s;
        cin >> s;
        int N = 1 << n;
        vector<bool> f(N);
        for (int mask = 0; mask < N; ++mask) {
            f[mask] = (s[mask] == '1');
        }
        // check monotonicity
        bool monotone = true;
        for (int mask = 0; mask < N; ++mask) {
            for (int i = 0; i < n; ++i) {
                if (!(mask & (1 << i))) {
                    int mask2 = mask | (1 << i);
                    if (f[mask] > f[mask2]) {
                        monotone = false;
                        break;
                    }
                }
            }
            if (!monotone) break;
        }
        if (!monotone) {
            cout << "No\n";
            continue;
        }
        // compute minterms
        vector<int> minterms;
        for (int mask = 0; mask < N; ++mask) {
            if (f[mask]) {
                bool minimal = true;
                for (int i = 0; i < n; ++i) {
                    if (mask & (1 << i)) {
                        int submask = mask ^ (1 << i);
                        if (f[submask]) {
                            minimal = false;
                            break;
                        }
                    }
                }
                if (minimal) {
                    minterms.push_back(mask);
                }
            }
        }
        // output
        cout << "Yes\n";
        if (minterms.empty()) {
            cout << "F\n";
        } else if (minterms.size() == 1 && minterms[0] == 0) {
            cout << "T\n";
        } else if (minterms.size() == 1) {
            int mask = minterms[0];
            vector<int> vars;
            for (int i = 0; i < n; ++i) {
                if (mask & (1 << i)) {
                    vars.push_back(i);
                }
            }
            sort(vars.begin(), vars.end());
            cout << build_and(vars) << "\n";
        } else {
            vector<string> terms;
            for (int mask : minterms) {
                vector<int> vars;
                for (int i = 0; i < n; ++i) {
                    if (mask & (1 << i)) {
                        vars.push_back(i);
                    }
                }
                sort(vars.begin(), vars.end());
                terms.push_back(build_and(vars));
            }
            cout << build_or(terms) << "\n";
        }
    }
    return 0;
}