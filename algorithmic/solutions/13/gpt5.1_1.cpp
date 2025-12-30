#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int sx, sy;
    if (!(cin >> sx >> sy)) return 0;

    int rx = sx, ry = sy;

    int mx = 1, my = 1;

    for (int step = 1; step <= 3000; ++step) {
        // Choose a cell to mark black (simple scan pattern)
        cout << mx << ' ' << my << '\n';
        cout.flush();

        // Read robot's new position
        if (!(cin >> rx >> ry)) break;
        if (rx == 0 && ry == 0) break;

        // Next cell in scan
        ++mx;
        if (mx > 3000) {
            mx = 1;
            ++my;
            if (my > 3000) my = 1;
        }
    }

    return 0;
}