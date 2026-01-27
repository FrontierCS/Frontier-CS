#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int d;
    if (!(cin >> d)) return 0;
    if (d == 0) return 0;

    int lastUp = -1; // color of edge leading back to the child we came from

    while (true) {
        vector<int> order;
        if (lastUp == -1) {
            order = {0, 1, 2};
        } else {
            order = {(lastUp + 1) % 3, (lastUp + 2) % 3};
        }

        bool movedUp = false;

        for (int c : order) {
            cout << "move " << c << endl;
            cout.flush();
            int r;
            if (!(cin >> r)) return 0;
            if (r == 1) return 0;

            cout << "query" << endl;
            cout.flush();
            int d2;
            if (!(cin >> d2)) return 0;

            if (d2 == d - 1) {
                d = d2;
                lastUp = c;
                movedUp = true;
                break;
            } else {
                // d2 == d + 1, move back
                cout << "move " << c << endl;
                cout.flush();
                if (!(cin >> r)) return 0;
                // back to original node
            }
        }

        if (!movedUp) {
            // As a safety fallback, try the remaining color (which must be up)
            if (lastUp != -1) {
                int c = lastUp;
                cout << "move " << c << endl;
                cout.flush();
                int r;
                if (!(cin >> r)) return 0;
                if (r == 1) return 0;

                cout << "query" << endl;
                cout.flush();
                int d2;
                if (!(cin >> d2)) return 0;

                if (d2 == d - 1) {
                    d = d2;
                    lastUp = c;
                } else {
                    // move back just in case
                    cout << "move " << c << endl;
                    cout.flush();
                    if (!(cin >> r)) return 0;
                }
            }
        }
    }

    return 0;
}