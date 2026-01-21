#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int d;
    if (!(cin >> d)) {
        return 0;
    }

    if (d == 0) {
        // Already at the exit
        return 0;
    }

    while (d > 0) {
        bool moved_to_parent = false;
        for (int c = 0; c < 3 && !moved_to_parent; ++c) {
            cout << "move " << c << endl;
            int res;
            if (!(cin >> res)) return 0;
            if (res == 1) {
                // Reached the exit
                return 0;
            }

            cout << "query" << endl;
            int nd;
            if (!(cin >> nd)) return 0;

            if (nd < d) {
                // This edge leads closer to the exit
                d = nd;
                moved_to_parent = true;
            } else {
                // This edge leads farther from the exit, go back
                cout << "move " << c << endl;
                if (!(cin >> res)) return 0;
                // res should be 0 here since we are not at the exit
            }
        }
    }

    return 0;
}