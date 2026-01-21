#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int d;
    if (!(cin >> d)) return 0;
    if (d == 0) {
        return 0;  // already at exit
    }

    while (true) {
        for (int c = 0; c < 3; ++c) {
            cout << "move " << c << '\n';
            cout.flush();
            int reached;
            if (!(cin >> reached)) return 0;
            if (reached == 1) {
                return 0;  // reached exit
            }

            cout << "query\n";
            cout.flush();
            int nd;
            if (!(cin >> nd)) return 0;

            if (nd == d - 1) {
                // moved towards exit
                d = nd;
                if (d == 0) return 0;
                break;  // go to next node
            } else if (nd == d + 1) {
                // moved away from exit, go back
                cout << "move " << c << '\n';
                cout.flush();
                int back;
                if (!(cin >> back)) return 0;
                // back should not reach exit here
                // depth returns to d
            } else {
                // unexpected, but just update and continue
                d = nd;
                if (d == 0) return 0;
                break;
            }
        }
    }

    return 0;
}