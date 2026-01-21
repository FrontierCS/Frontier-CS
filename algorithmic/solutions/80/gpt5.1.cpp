#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int m;
    if (!(cin >> m)) return 0;

    string loc;
    if (!(cin >> loc)) return 0;
    if (loc == "treasure") return 0;

    mt19937 rng((unsigned)chrono::steady_clock::now().time_since_epoch().count());
    int steps = 0;
    const int MAX_STEPS = 50000;

    while (steps < MAX_STEPS) {
        if (loc == "treasure") break;

        int place = rng() % m;
        int go = rng() % m;
        string side = (loc == "left" ? "right" : "left");

        cout << place << ' ' << side << ' ' << go << endl;
        cout.flush();
        ++steps;

        if (!(cin >> loc)) break;
        if (loc == "treasure") break;
    }

    return 0;
}