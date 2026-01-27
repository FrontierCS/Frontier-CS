#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int d;
    if (!(cin >> d)) return 0;
    if (d == 0) return 0;

    while (d > 0) {
        for (int c = 0; c < 3; ++c) {
            cout << "move " << c << endl;
            int reached;
            if (!(cin >> reached)) return 0;
            if (reached == 1) return 0;

            cout << "query" << endl;
            int nd;
            if (!(cin >> nd)) return 0;

            if (nd == d - 1) {
                d = nd;
                break;
            } else {
                // Went further from exit; backtrack
                cout << "move " << c << endl;
                if (!(cin >> reached)) return 0; // should be 0
            }
        }
    }
    return 0;
}