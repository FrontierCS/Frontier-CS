#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int initialDeep;
    if (!(cin >> initialDeep)) return 0;

    int curDist = initialDeep;

    if (curDist == 0) {
        // Already at exit
        return 0;
    }

    while (true) {
        // We know curDist > 0
        for (int c = 0; c < 3; ++c) {
            cout << "move " << c << '\n';
            cout.flush();
            int reached;
            if (!(cin >> reached)) return 0;

            if (reached == 1) {
                // Reached exit; do not move further
                return 0;
            }

            cout << "query\n";
            cout.flush();
            int newDist;
            if (!(cin >> newDist)) return 0;

            if (newDist == curDist - 1) {
                curDist = newDist;
                if (curDist == 0) {
                    // Should not happen because 'reached' would have been 1,
                    // but in any case we are at exit now.
                    return 0;
                }
                // Found parent direction; go to next level towards exit
                break;
            } else {
                // Must be newDist == curDist + 1 (moved away); go back
                cout << "move " << c << '\n';
                cout.flush();
                int backReached;
                if (!(cin >> backReached)) return 0;
                // backReached should be 0 since we return to a non-exit node
                // curDist remains unchanged
            }
        }
    }

    return 0;
}