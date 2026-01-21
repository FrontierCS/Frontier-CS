#include <bits/stdc++.h>
using namespace std;

static inline bool doMove(int c, int &resp) {
    cout << "move " << c << "\n" << flush;
    if (!(cin >> resp)) return false;
    return true;
}

static inline bool doQuery(int &dist) {
    cout << "query\n" << flush;
    if (!(cin >> dist)) return false;
    return true;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int cur;
    if (!(cin >> cur)) return 0;
    if (cur == 0) return 0;

    while (true) {
        bool progressed = false;
        for (int c = 0; c < 3; c++) {
            int r;
            if (!doMove(c, r)) return 0;
            if (r == 1) return 0;

            int nd;
            if (!doQuery(nd)) return 0;

            if (nd < cur) {
                cur = nd;
                progressed = true;
                break;
            } else {
                int rb;
                if (!doMove(c, rb)) return 0;
                if (rb == 1) return 0;
            }
        }
        if (!progressed) return 0; // should not happen in valid tests
    }
    return 0;
}