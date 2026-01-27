#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;
    string s, tok;
    bool found = false;
    while (cin >> tok) {
        bool ok = (int)tok.size() == n;
        if (ok) {
            for (char c : tok) {
                if (c != '(' && c != ')') { ok = false; break; }
            }
        }
        if (ok) { s = tok; found = true; break; }
    }
    if (!found) {
        s.reserve(n);
        for (int i = 0; i < n/2; ++i) s += "()";
        if ((int)s.size() < n) s += '(';
        while ((int)s.size() < n) s += ')';
    }
    cout << "1 " << s << "\n";
    cout.flush();
    return 0;
}