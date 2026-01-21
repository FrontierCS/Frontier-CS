#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int m;
    if (!(cin >> m)) return 0;

    string pos;
    if (!(cin >> pos)) return 0;

    int steps = 0;
    while (steps < 50000 && pos != "treasure") {
        int place = 0;
        int take = 0;
        string side = "left";

        if (pos == "center") {
            place = 0;
            take = 0;
            side = "left";
        } else if (pos == "left") {
            place = 1 % m; // m >= 2
            take = 0;
            side = "left";
        } else if (pos == "right") {
            place = 1 % m;
            take = 0;
            side = "right";
        }

        cout << place << ' ' << side << ' ' << take << '\n';
        cout.flush();
        ++steps;

        if (!(cin >> pos)) break;
    }

    return 0;
}