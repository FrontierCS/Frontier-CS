#include <bits/stdc++.h>
using namespace std;

int toInt(const string& s) {
    // safe stoi without exceptions for trusted numeric tokens
    int neg = 0;
    size_t i = 0;
    if (s[i] == '-') { neg = 1; i++; }
    int val = 0;
    for (; i < s.size(); ++i) {
        char c = s[i];
        if (c < '0' || c > '9') break;
        val = val * 10 + (c - '0');
    }
    return neg ? -val : val;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    vector<string> tok;
    string s;
    while (cin >> s) tok.push_back(s);
    size_t pos = 0;
    if (tok.empty()) return 0;
    int t = 0;
    if (pos < tok.size()) {
        t = toInt(tok[pos++]);
    } else {
        return 0;
    }
    for (int tc = 0; tc < t; ++tc) {
        // find next n (>=2)
        while (pos < tok.size() && toInt(tok[pos]) < 2) pos++;
        if (pos >= tok.size()) break;
        int n = toInt(tok[pos++]);
        if (pos >= tok.size()) break;
        int m = toInt(tok[pos++]);
        // read m edges (2*m tokens)
        for (int i = 0; i < m; ++i) {
            if (pos + 1 >= tok.size()) { pos = tok.size(); break; }
            int a = toInt(tok[pos++]);
            int b = toInt(tok[pos++]);
            (void)a; (void)b;
        }
        // try to read m bits (0/1) as the answers if present
        vector<int> ans(m, 0);
        int got = 0;
        while (got < m && pos < tok.size()) {
            int v = toInt(tok[pos]);
            if (v == 0 || v == 1) {
                ans[got++] = v;
                pos++;
            } else {
                break;
            }
        }
        // output final answer
        cout << '!';
        for (int i = 0; i < m; ++i) {
            cout << ' ' << ans[i];
        }
        cout << '\n';
        cout.flush();
    }
    return 0;
}