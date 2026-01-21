#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int d;
    if (!(cin >> d)) return 0;
    if (d == 0) return 0;

    while (d > 0) {
        bool movedToParent = false;
        for (int c = 0; c < 2; ++c) {
            cout << "move " << c << endl;
            cout.flush();
            int retMove;
            if (!(cin >> retMove)) return 0;
            if (retMove == 1) return 0;

            cout << "query" << endl;
            cout.flush();
            int nd;
            if (!(cin >> nd)) return 0;

            if (nd < d) { // moved towards exit
                d = nd;
                movedToParent = true;
                break;
            } else {
                // moved away; go back
                cout << "move " << c << endl;
                cout.flush();
                int retBack;
                if (!(cin >> retBack)) return 0;
                if (retBack == 1) return 0;
                // now back at original node with depth d
            }
        }
        if (!movedToParent) {
            // The remaining color must lead to the parent
            cout << "move " << 2 << endl;
            cout.flush();
            int retFinal;
            if (!(cin >> retFinal)) return 0;
            if (retFinal == 1) return 0;
            --d;
        }
    }

    return 0;
}