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
            cout.flush();
        } else if (s == "left") {
            int step = 1 % m;
            cout << step << " left " << step << endl;
            cout.flush();
        } else if (s == "right") {
            int step = 1 % m;
            cout << step << " right " << step << endl;
            cout.flush();
        } else {
            // Unexpected input; stop to avoid undefined behavior.
            break;
        }
    }
    return 0;
}