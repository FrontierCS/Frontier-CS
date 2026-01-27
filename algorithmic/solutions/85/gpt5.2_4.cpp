#include <bits/stdc++.h>
using namespace std;

static bool readInt(int &x) {
    if (!(cin >> x)) return false;
    return true;
}

static bool doMove(int c) {
    cout << "move " << c << endl; // endl flushes
    int reached = 0;
    if (!readInt(reached)) exit(0);
    return reached == 1;
}

static int doQuery() {
    cout << "query" << endl;
    int d = 0;
    if (!readInt(d)) exit(0);
    return d;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int d;
    if (!readInt(d)) return 0;
    if (d == 0) return 0;

    int lastColor = -1; // color used to arrive at current node (known only after first confirmed up-move)

    while (d > 0) {
        vector<int> cand;
        if (lastColor == -1) {
            cand = {0, 1, 2};
        } else {
            for (int c = 0; c < 3; c++) if (c != lastColor) cand.push_back(c);
        }

        int c1 = cand[0];
        if (doMove(c1)) return 0;
        int nd1 = doQuery();
        if (nd1 == d - 1) {
            d = nd1;
            lastColor = c1;
            continue;
        }

        // wrong direction, go back
        if (doMove(c1)) return 0;

        if ((int)cand.size() == 2) {
            int c2 = cand[1];
            if (doMove(c2)) return 0;
            d -= 1;
            lastColor = c2;
            continue;
        } else {
            int c2 = cand[1];
            if (doMove(c2)) return 0;
            int nd2 = doQuery();
            if (nd2 == d - 1) {
                d = nd2;
                lastColor = c2;
                continue;
            }

            // second wrong, go back
            if (doMove(c2)) return 0;

            int c3 = 3 - c1 - c2;
            if (doMove(c3)) return 0;
            d -= 1;
            lastColor = c3;
            continue;
        }
    }

    return 0;
}