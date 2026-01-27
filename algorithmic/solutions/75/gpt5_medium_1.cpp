#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int b, w, x, y;
    if (!(cin >> b >> w >> x >> y)) return 0;

    const int R = 100, C = 100;
    vector<string> grid(R, string(C, '@'));
    // Top half black '@', bottom half white '.'
    for (int r = R / 2; r < R; ++r) {
        grid[r] = string(C, '.');
    }

    // Place white islands in top half to make (w-1) extra white components
    int white_need = w - 1;
    for (int r = 1; r < R/2 - 1 && white_need > 0; r += 2) {
        for (int c = 1; c < C - 1 && white_need > 0; c += 2) {
            grid[r][c] = '.';
            --white_need;
        }
    }

    // Place black islands in bottom half to make (b-1) extra black components
    int black_need = b - 1;
    for (int r = R/2 + 1; r < R && black_need > 0; r += 2) {
        for (int c = 1; c < C - 1 && black_need > 0; c += 2) {
            grid[r][c] = '@';
            --black_need;
        }
    }

    cout << R << " " << C << "\n";
    for (int r = 0; r < R; ++r) {
        cout << grid[r] << "\n";
    }
    return 0;
}