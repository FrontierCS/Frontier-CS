#include <bits/stdc++.h>
using namespace std;

static inline bool do_move(int c, int &reached) {
    cout << "move " << c << '\n' << flush;
    if (!(cin >> reached)) return false;
    return true;
}

static inline bool do_query(int &dist) {
    cout << "query\n" << flush;
    if (!(cin >> dist)) return false;
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int dist;
    if (!(cin >> dist)) return 0;

    if (dist == 0) return 0;

    int lastColor = -1; // color of edge leading back to the node we came from (away from exit)
    while (dist > 0) {
        int parentColor = -1;

        for (int c = 0; c < 3; c++) {
            if (c == lastColor) continue;

            int reached = 0;
            if (!do_move(c, reached)) return 0;
            if (reached == 1) return 0;

            int ndist = -1;
            if (!do_query(ndist)) return 0;

            if (ndist == dist - 1) {
                parentColor = c;
                dist = ndist;
                lastColor = c;
                break;
            } else {
                int backReached = 0;
                if (!do_move(c, backReached)) return 0;
                // backReached should be 0 here
            }
        }

        if (parentColor == -1) return 0; // should not happen
    }

    return 0;
}