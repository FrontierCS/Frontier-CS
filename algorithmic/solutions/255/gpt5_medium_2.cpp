#include <bits/stdc++.h>
using namespace std;

bool isNSDashStr(const string &s) {
    for (char c : s) {
        if (c != 'N' && c != 'S' && c != '-') return false;
    }
    return !s.empty();
}

bool isInteger(const string &s) {
    if (s.empty()) return false;
    size_t i = 0;
    if (s[0] == '-' || s[0] == '+') i = 1;
    if (i >= s.size()) return false;
    for (; i < s.size(); ++i) if (!isdigit(s[i])) return false;
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        if (!(cin >> n)) break;

        vector<char> types;
        types.reserve(n);
        while ((int)types.size() < n) {
            string tok;
            if (!(cin >> tok)) break;

            if (isNSDashStr(tok)) {
                if ((int)tok.size() == n && types.empty()) {
                    for (int i = 0; i < n; ++i) types.push_back(tok[i]);
                } else if (tok.size() == 1) {
                    types.push_back(tok[0]);
                } else {
                    for (char c : tok) {
                        if ((int)types.size() < n) types.push_back(c);
                    }
                }
            } else if (isInteger(tok)) {
                long long v = stoll(tok);
                char c;
                if (v == 0 || v == -1) c = '-';
                else if (v == 1) c = 'N';
                else if (v == 2) c = 'S';
                else c = '-';
                types.push_back(c);
            } else {
                // Unrecognized token; ignore
            }
        }

        vector<int> ans;
        for (int i = 0; i < (int)types.size(); ++i) {
            if (types[i] == '-') ans.push_back(i + 1);
        }
        cout << ans.size();
        for (int x : ans) cout << ' ' << x;
        cout << '\n';
    }
    return 0;
}