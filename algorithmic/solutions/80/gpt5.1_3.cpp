#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int m;
    if (!(cin >> m)) return 0;

    string pos;
    if (!(cin >> pos)) return 0;

    while (true) {
        if (pos == "treasure") {
            return 0;
        }

        int moveStone, takePass;
        if (pos == "center") {
            moveStone = 0;
            takePass = 0;
        } else {
            moveStone = 1 % m;
            takePass = 1 % m;
        }

        cout << moveStone << " left " << takePass << endl;
        cout.flush();

        if (!(cin >> pos)) return 0;
    }

    return 0;
}