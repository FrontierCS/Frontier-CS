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

        int moveStone = 0, takePassage = 0;
        const char* side = "left";

        if (s == "center") {
            // First time in this chamber: fix an arbitrary local reference and leave.
            moveStone = 0;
            takePassage = 0;
            side = "left";
        } else {
            // Rotor-router: advance to next passage and take it.
            moveStone = 1 % m;
            takePassage = 1 % m;
            side = "left";
        }

        cout << moveStone << ' ' << side << ' ' << takePassage << endl;

        if (!(cin >> s)) break;
    }

    return 0;
}