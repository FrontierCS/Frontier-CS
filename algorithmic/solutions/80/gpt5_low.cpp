#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int m;
    if (!(cin >> m)) return 0;

    string s;
    while (cin >> s) {
        if (s == "treasure") {
            break;
        }

        if (s == "center") {
            cout << 0 << " left " << 0 << "\n";
            cout.flush();
        } else if (s == "left") {
            cout << 1 % m << " left " << 1 % m << "\n";
            cout.flush();
        } else if (s == "right") {
            // Convert to 'left' at the same passage and take it
            cout << 0 << " left " << 0 << "\n";
            cout.flush();
        } else {
            // Unexpected input; terminate to avoid protocol violation
            break;
        }
    }
    return 0;
}