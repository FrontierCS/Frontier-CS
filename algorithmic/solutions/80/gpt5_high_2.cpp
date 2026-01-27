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
        // Rotate stone by 1, set to left, take current passage
        cout << 1 % m << " left " << 0 << endl;
    }
    return 0;
}