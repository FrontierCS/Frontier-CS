#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int sx, sy;
    if (!(cin >> sx >> sy)) return 0;
    int rx = sx, ry = sy;

    // Naive interactive strategy: always paint the cell (1,1)
    // This is just a placeholder strategy to comply with the interactive protocol.
    for (int t = 1; t <= 3000; ++t) {
        int mx = 1, my = 1;
        cout << mx << ' ' << my << '\n';
        cout.flush();

        int nx, ny;
        if (!(cin >> nx >> ny)) return 0;
        if (nx == 0 && ny == 0) break; // robot exploded
        rx = nx; ry = ny;
    }

    return 0;
}