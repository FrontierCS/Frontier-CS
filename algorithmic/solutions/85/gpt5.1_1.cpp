#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int d;
    if (!(cin >> d)) return 0;

    if (d == 0) {
        // Already at the exit; do nothing.
        return 0;
    }

    int from_color = -1; // color of edge leading back to the previous (deeper) node

    while (d > 0) {
        bool moved_toward_exit = false;

        for (int c = 0; c < 3 && !moved_toward_exit; ++c) {
            if (from_color != -1 && c == from_color) continue; // known child, skip

            cout << "move " << c << endl;
            int isExit;
            if (!(cin >> isExit)) return 0;
            if (isExit == 1) {
                // Reached the exit; must not move anymore.
                return 0;
            }

            cout << "query" << endl;
            int newD;
            if (!(cin >> newD)) return 0;

            if (newD < d) {
                // Moved toward exit (to parent)
                from_color = c; // this edge now points back to the child
                d = newD;
                moved_toward_exit = true;
            } else if (newD > d) {
                // Moved away from exit (to child), go back immediately
                cout << "move " << c << endl;
                if (!(cin >> isExit)) return 0; // should be 0
            } else {
                // Invalid response; terminate
                return 0;
            }
        }

        if (!moved_toward_exit) {
            // Should not happen in a valid tree
            return 0;
        }
    }

    return 0;
}