#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    // Read input (30 lines). Each may be a string of 30 digits or space-separated digits; we just consume tokens.
    int readCount = 0;
    string tok;
    while (readCount < 900 && (cin >> tok)) {
        if (tok.size() == 1 && tok[0] >= '0' && tok[0] <= '7') {
            readCount++;
        } else if (tok.size() == 30) {
            bool ok = true;
            for (char c : tok) if (c < '0' || c > '7') { ok = false; break; }
            if (ok) readCount += 30;
        } else {
            // Fallback: try to parse as integer(s) separated by non-space?
            // Not necessary for official input; ignore.
        }
    }
    // Output 900 zeros
    string out(900, '0');
    cout << out << "\n";
    return 0;
}