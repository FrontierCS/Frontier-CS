#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int m;
    if (!(cin >> m)) return 0;
    string line;
    getline(cin, line); // consume end of line after m

    // Read initial state
    if (!getline(cin, line)) return 0;

    // Simple pseudorandom generator (deterministic)
    uint64_t rng = 88172645463393265ULL;
    auto nextRand = [&]() -> uint64_t {
        rng ^= rng << 7;
        rng ^= rng >> 9;
        return rng;
    };

    long long steps = 0;
    while (steps < 50000) {
        // Parse line: could be "center", "left", "right", or "treasure"
        string pos;
        {
            stringstream ss(line);
            ss >> pos;
        }

        if (pos == "treasure") break;
        if (pos != "center" && pos != "left" && pos != "right") break;

        int placeOffset = (int)(nextRand() % m);
        string side = (nextRand() & 1) ? "left" : "right";
        int takePass = (int)(nextRand() % m);

        cout << placeOffset << ' ' << side << ' ' << takePass << '\n';
        cout.flush();
        ++steps;

        if (!getline(cin, line)) break;
    }

    return 0;
}