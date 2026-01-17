#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int m;
    if (!(cin >> m)) return 0;
    string s;
    while (cin >> s) {
        if (s == "treasure") break;
        if (s == "center") {
            cout << 0 << " left " << 0 << endl;
        } else if (s == "left" || s == "right") {
            int step = 1 % m;
            cout << step << " left " << step << endl;
        } else {
            // Unexpected input; terminate to avoid protocol violation
            break;
        }
    }
    return 0;
}