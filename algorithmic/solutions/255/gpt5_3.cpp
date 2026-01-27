#include <bits/stdc++.h>
using namespace std;

bool isInteger(const string &s) {
    if (s.empty()) return false;
    size_t i = 0;
    if (s[0] == '+' || s[0] == '-') i = 1;
    if (i == s.size()) return false;
    for (; i < s.size(); ++i) if (!isdigit((unsigned char)s[i])) return false;
    return true;
}

bool allowedCharsOnly(const string &s) {
    for (char c : s) {
        if (!(c == 'N' || c == 'S' || c == '-' || c == 'n' || c == 's' || c == '0' || c == '1' || c == '2'))
            return false;
    }
    return true;
}

bool isZeroToken(const string &tok) {
    if (tok.size() == 1) {
        char c = tok[0];
        if (c == '-' || c == '0') return true;
        if (c == 'N' || c == 'n' || c == 'S' || c == 's' || c == '1' || c == '2') return false;
    }
    if (isInteger(tok)) {
        long long v = 0;
        try {
            v = stoll(tok);
        } catch (...) {
            return false;
        }
        return v == 0;
    }
    return false;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        if (!(cin >> n)) break;
        vector<int> zeros;
        string tok;
        if (!(cin >> tok)) break;

        if ((int)tok.size() == n && allowedCharsOnly(tok)) {
            for (int i = 0; i < n; ++i) {
                char c = tok[i];
                if (c == '-' || c == '0') zeros.push_back(i + 1);
            }
        } else {
            if (isZeroToken(tok)) zeros.push_back(1);
            for (int i = 2; i <= n; ++i) {
                string t2;
                cin >> t2;
                if (isZeroToken(t2)) zeros.push_back(i);
            }
        }

        cout << zeros.size();
        for (int idx : zeros) cout << ' ' << idx;
        cout << '\n';
    }
    return 0;
}