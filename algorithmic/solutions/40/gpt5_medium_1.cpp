#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    if (!(cin >> n)) return 0;

    // Read the rest of input
    string rest, tok, full;
    {
        std::ostringstream oss;
        while (cin >> tok) {
            oss << tok << ' ';
        }
        rest = oss.str();
    }

    // Extract any sequence of '(' and ')' of length n from the rest (ignoring spaces)
    string only;
    for (char c : rest) {
        if (c == '(' || c == ')') only.push_back(c);
    }

    string s;
    if ((int)only.size() >= n) {
        s = only.substr(0, n);
    } else {
        // Fallback: produce a simple bracket string of length n
        // Use alternating pattern "()"...
        s.reserve(n);
        for (int i = 0; i < n; ++i) {
            s.push_back((i % 2 == 0) ? '(' : ')');
        }
    }

    cout << "1 " << s << "\n" << flush;
    return 0;
}