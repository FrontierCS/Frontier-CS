#include <bits/stdc++.h>
using namespace std;

string s;
int n, N;

string build(int lo, int m, int fixed) {
    if (m == 0) {
        return s[fixed] == '1' ? "T" : "F";
    }
    int fixed0 = fixed;
    int fixed1 = fixed | (1 << lo);
    string e0 = build(lo + 1, m - 1, fixed0);
    string e1 = build(lo + 1, m - 1, fixed1);
    bool eq = true;
    int subn = 1 << (m - 1);
    int shift = lo + 1;
    for (int k = 0; k < subn; ++k) {
        int pos0 = fixed0 | (k << shift);
        int pos1 = fixed1 | (k << shift);
        if (s[pos0] != s[pos1]) {
            eq = false;
            break;
        }
    }
    if (eq) {
        return e0;
    }
    char v = 'a' + lo;
    string res;
    if (e0 == "F") {
        if (e1 == "T") {
            res = string(1, v);
        } else {
            res = "(" + string(1, v) + "&" + e1 + ")";
        }
    } else if (e1 == "T") {
        res = "(" + e0 + "|" + string(1, v) + ")";
    } else {
        string inner = "(" + string(1, v) + "&" + e1 + ")";
        res = "(" + e0 + "|" + inner + ")";
    }
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int T;
    cin >> T;
    for (int t = 0; t < T; ++t) {
        cin >> n;
        cin >> s;
        N = 1 << n;
        bool mono = true;
        for (int mask = 0; mask < N; ++mask) {
            if (s[mask] == '1') {
                for (int i = 0; i < n; ++i) {
                    if ((mask & (1 << i)) == 0) {
                        int nm = mask | (1 << i);
                        if (s[nm] == '0') {
                            mono = false;
                            goto nxt;
                        }
                    }
                }
            }
        }
    nxt:;
        if (!mono) {
            cout << "No\n";
            continue;
        }
        string expr = build(0, n, 0);
        cout << "Yes\n" << expr << "\n";
    }
    return 0;
}