#include <bits/stdc++.h>
using namespace std;

static void die() { exit(0); }

static int do_move(int c) {
    cout << "move " << c << '\n' << flush;
    int res;
    if (!(cin >> res)) die();
    if (res == -1) die();
    return res;
}

static int do_query() {
    cout << "query" << '\n' << flush;
    int d;
    if (!(cin >> d)) die();
    if (d == -1) die();
    return d;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int d;
    if (!(cin >> d)) return 0;
    if (d == 0) return 0;

    int backColor = -1; // color of edge leading back to the deeper node we came from

    while (true) {
        vector<int> cand;
        cand.reserve(3);
        for (int c = 0; c < 3; c++) if (c != backColor) cand.push_back(c);
        if (cand.empty()) cand = {0, 1, 2};

        bool movedUp = false;

        for (int c : cand) {
            int reached = do_move(c);
            if (reached == 1) return 0;

            int d2 = do_query();
            if (d2 == d - 1) {
                d = d2;
                backColor = c;
                movedUp = true;
                break;
            } else {
                // went down to a child, go back
                reached = do_move(c);
                if (reached == 1) return 0; // should not happen
            }
        }

        if (!movedUp) {
            // Fallback: try all colors (shouldn't be needed)
            for (int c = 0; c < 3; c++) {
                int reached = do_move(c);
                if (reached == 1) return 0;
                int d2 = do_query();
                if (d2 == d - 1) {
                    d = d2;
                    backColor = c;
                    movedUp = true;
                    break;
                } else {
                    reached = do_move(c);
                    if (reached == 1) return 0;
                }
            }
            if (!movedUp) die();
        }

        if (d == 0) return 0; // in case query indicates exit (some judges may allow this)
    }
}