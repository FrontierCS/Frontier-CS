#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int d;
    if (!(cin >> d)) return 0;
    if (d == 0) return 0;

    while (true) {
        if (d == 0) break;
        bool progressed = false;
        for (int c = 0; c < 3; ++c) {
            cout << "move " << c << endl;
            cout.flush();
            int r;
            if (!(cin >> r)) return 0;
            if (r == 1) return 0;

            cout << "query" << endl;
            cout.flush();
            int d2;
            if (!(cin >> d2)) return 0;

            if (d2 < d) {
                d = d2;
                progressed = true;
                if (d == 0) return 0;
                break;
            } else {
                // backtrack
                cout << "move " << c << endl;
                cout.flush();
                int r2;
                if (!(cin >> r2)) return 0;
                if (r2 == 1) return 0; // should not happen in a consistent model

                cout << "query" << endl;
                cout.flush();
                int dback;
                if (!(cin >> dback)) return 0;
                d = dback; // should be equal to previous d
            }
        }
        // In a proper tree, we must have progressed
        if (!progressed) break;
    }

    return 0;
}