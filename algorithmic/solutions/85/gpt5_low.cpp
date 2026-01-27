#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int d;
    if (!(cin >> d)) return 0; // initialDeep

    if (d == 0) return 0;

    while (true) {
        // At current node with depth d
        for (int c = 0; c < 3; ++c) {
            cout << "move " << c << "\n" << flush;
            int reached;
            if (!(cin >> reached)) return 0;
            if (reached == 1) return 0; // reached exit

            cout << "query\n" << flush;
            int d2;
            if (!(cin >> d2)) return 0;

            if (d2 == d - 1) {
                // Moved towards exit; update depth and continue from new node
                d = d2;
                if (d == 0) return 0;
                break;
            } else {
                // We must have gone deeper (d2 == d + 1), backtrack using same color
                cout << "move " << c << "\n" << flush;
                int reached2;
                if (!(cin >> reached2)) return 0; // should be 0
                // Query to sync depth back to d
                cout << "query\n" << flush;
                int d_back;
                if (!(cin >> d_back)) return 0;
                d = d_back; // should equal original d
                // try next color
            }
        }
    }
    return 0;
}