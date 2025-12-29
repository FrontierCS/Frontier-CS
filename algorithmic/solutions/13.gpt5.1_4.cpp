#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int rx, ry;
    if (!(cin >> rx >> ry)) return 0; // Initial robot position

    const int T = 3000;
    static bool black[3001][3001] = {0};

    // Preferred order of cells to paint around the robot (including its cell)
    int order[9][2] = {
        {0, 0},
        {-1, 0}, {1, 0},
        {0, -1}, {0, 1},
        {-1, -1}, {-1, 1},
        {1, -1}, {1, 1}
    };

    for (int step = 1; step <= T; ++step) {
        int mx = 1, my = 1;
        bool chosen = false;

        // Try to paint an unpainted cell in the 3x3 neighborhood
        for (int k = 0; k < 9; ++k) {
            int nx = rx + order[k][0];
            int ny = ry + order[k][1];
            if (nx < 1 || nx > T || ny < 1 || ny > T) continue;
            if (!black[nx][ny]) {
                mx = nx;
                my = ny;
                chosen = true;
                break;
            }
        }

        if (!chosen) {
            // Fallback: paint the robot's current cell (clamped, though it's within range)
            mx = min(max(rx, 1), T);
            my = min(max(ry, 1), T);
        }

        black[mx][my] = true;
        cout << mx << ' ' << my << '\n';
        cout.flush();

        int nx, ny;
        if (!(cin >> nx >> ny)) return 0;
        if (nx == 0 && ny == 0) break;
        rx = nx;
        ry = ny;
    }

    return 0;
}