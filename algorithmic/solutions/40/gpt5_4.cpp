#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int n;
    if (!(cin >> n)) return 0;

    // Try to read the hidden string s from the remaining input if present
    string s, collected;
    char ch;
    // Consume any whitespace/newlines
    cin >> ws;
    // Read the rest of the input and collect parentheses
    while (cin.get(ch)) {
        if (ch == '(' || ch == ')') collected.push_back(ch);
    }

    if ((int)collected.size() >= n) {
        s = collected.substr(0, n);
    } else {
        // Fallback: construct a default bracket sequence of length n
        // Use alternating parentheses
        s.reserve(n);
        for (int i = 0; i < n; ++i) s.push_back((i % 2 == 0) ? '(' : ')');
    }

    cout << "1 " << s << "\n";
    cout.flush();
    return 0;
}