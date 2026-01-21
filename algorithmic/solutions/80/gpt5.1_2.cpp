#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int m;
    if (!(cin >> m)) return 0;

    string pos;
    int curPort = 0;

    while (cin >> pos) {
        if (pos == "treasure") break;
        cout << 0 << " left " << curPort << endl;
        curPort = (curPort + 1) % m;
    }

    return 0;
}