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
        int moveOffset = (m >= 2 ? 1 : 0);
        int takeOffset = (m >= 2 ? 1 : 0);
        cout << moveOffset << " left " << takeOffset << endl;
    }
    return 0;
}