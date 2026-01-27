#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int sx, sy;
    if (!(cin >> sx >> sy)) return 0;

    int rx = sx, ry = sy;
    const int T = 3000;

    for (int step = 0; step < T; ++step) {
        int px = min(rx + 1, T);
        int py = min(ry + 1, T);
        cout << px << " " << py << endl;

        int nx, ny;
        if (!(cin >> nx >> ny)) return 0;
        if (nx == 0 && ny == 0) return 0;

        rx = nx;
        ry = ny;
    }

    return 0;
}