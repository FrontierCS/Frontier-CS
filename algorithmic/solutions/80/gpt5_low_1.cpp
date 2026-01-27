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
            return 0;
        } else if (s == "center") {
            cout << 0 << " left " << 0 << endl;
        } else if (s == "left") {
            cout << 1 % m << " left " << 1 % m << endl;
        } else if (s == "right") {
            cout << 1 % m << " right " << 1 % m << endl;
        } else {
            // Unexpected input; terminate gracefully
            return 0;
        }
    }
    return 0;
}