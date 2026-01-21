#include <bits/stdc++.h>
using namespace std;

bool isBracketString(const string &s) {
    if (s.empty()) return false;
    for (char c : s) {
        if (c != '(' && c != ')') return false;
    }
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    vector<string> tok;
    string x;
    while (cin >> x) tok.push_back(x);
    if (tok.empty()) return 0;

    // Case 1: single test, format: n s
    if (tok.size() == 2 && isBracketString(tok[1])) {
        string s = tok[1];
        cout << "1 " << s << '\n';
        return 0;
    }

    // Case 2: multiple tests, format: T, then for each: n_i s_i
    if (!tok.empty()) {
        int T = stoi(tok[0]);
        int expected = 1 + 2 * T;
        if ((int)tok.size() == expected) {
            for (int i = 0; i < T; ++i) {
                string s = tok[1 + 2 * i + 1];
                cout << "1 " << s << '\n';
            }
            return 0;
        }
    }

    // Fallback: assume last token is the bracket string
    string s = tok.back();
    if (isBracketString(s)) {
        cout << "1 " << s << '\n';
    }
    return 0;
}