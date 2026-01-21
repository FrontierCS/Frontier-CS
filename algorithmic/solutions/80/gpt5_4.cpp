#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int m;
    if (!(cin >> m)) return 0;

    string s;
    if (!(cin >> s)) return 0;

    while (true) {
        if (s == "treasure") break;
        cout << "0 left 0" << endl;
        if (!(cin >> s)) break;
    }

    return 0;
}