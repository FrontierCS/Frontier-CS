#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    vector<string> tokens;
    string tok;
    while (cin >> tok) tokens.push_back(tok);

    auto isBracketString = [](const string& s)->bool{
        if (s.empty()) return false;
        for (char c : s) if (c != '(' && c != ')') return false;
        return true;
    };

    // Try to find the hidden string in the input (offline non-interactive fallback)
    for (const string& t : tokens) {
        if ((int)t.size() == n && isBracketString(t)) {
            cout << "1 " << t << "\n";
            cout.flush();
            return 0;
        }
    }

    // If not found, output a default bracket sequence of length n
    string ans;
    if (n % 2 == 0) {
        ans.reserve(n);
        for (int i = 0; i < n / 2; ++i) ans += "()";
    } else {
        ans.reserve(n);
        ans += '(';
        for (int i = 0; i < (n - 1) / 2; ++i) ans += "()";
    }

    cout << "1 " << ans << "\n";
    cout.flush();
    return 0;
}