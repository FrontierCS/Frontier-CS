#include <bits/stdc++.h>
using namespace std;

bool isInteger(const string &s) {
    if (s.empty()) return false;
    size_t i = 0;
    if (s[0] == '+' || s[0] == '-') {
        if (s.size() == 1) return false;
        i = 1;
    }
    for (; i < s.size(); ++i) {
        if (!isdigit(static_cast<unsigned char>(s[i]))) return false;
    }
    return true;
}

bool isValidMagChars(const string &s) {
    if (s.empty()) return false;
    for (char c : s) {
        if (c=='N'||c=='n'||c=='S'||c=='s'||c=='-'||c=='0'||c=='1'||c=='2') continue;
        return false;
    }
    return true;
}

int charToVal(char c) {
    if (c=='-' || c=='0') return 0; // demagnetized
    return 1; // any non-zero (N/S or other encoded) treated as non-demagnetized
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if (!(cin >> t)) return 0;
    for (int _case = 0; _case < t; ++_case) {
        int n;
        if (!(cin >> n)) break;
        vector<int> a(n, 1); // 1 means not '-', 0 means '-'
        string tok;
        if (!(cin >> tok)) tok = "";
        if ((int)tok.size() == n && isValidMagChars(tok)) {
            for (int i = 0; i < n; ++i) a[i] = charToVal(tok[i]);
        } else if (!tok.empty() && !isInteger(tok)) {
            // Read as n separate char tokens
            a[0] = charToVal(tok[0]);
            for (int i = 1; i < n; ++i) {
                string s; cin >> s;
                a[i] = charToVal(s.empty() ? '-' : s[0]);
            }
        } else {
            // Read as n integers (first one is tok)
            long long x = 0;
            if (!tok.empty() && isInteger(tok)) {
                x = stoll(tok);
            }
            a[0] = (x == 0 ? 0 : 1);
            for (int i = 1; i < n; ++i) {
                long long y; cin >> y;
                a[i] = (y == 0 ? 0 : 1);
            }
        }
        vector<int> ans;
        for (int i = 0; i < n; ++i) if (a[i] == 0) ans.push_back(i + 1);
        cout << ans.size();
        for (int idx : ans) cout << ' ' << idx;
        cout << '\n';
    }
    return 0;
}