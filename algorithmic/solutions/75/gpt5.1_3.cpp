#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int b, w, x, y;
    if (!(cin >> b >> w >> x >> y)) return 0;

    const int R = 100, C = 100;
    vector<string> grid(R, string(C, '@'));

    // Top half white, bottom half black
    for (int i = 0; i < R; ++i) {
        for (int j = 0; j < C; ++j) {
            if (i < 50) grid[i][j] = '.';
            else grid[i][j] = '@';
        }
    }

    int add_black = b - 1; // additional black components in top (white) half
    int add_white = w - 1; // additional white components in bottom (black) half

    // Place isolated black cells in the top half, avoiding the boundary row (49)
    for (int i = 0; i < 49 && add_black > 0; i += 2) {
        for (int j = 0; j < C && add_black > 0; j += 2) {
            grid[i][j] = '@';
            --add_black;
        }
    }

    // Place isolated white cells in the bottom half, avoiding the boundary row (50)
    for (int i = 51; i < R && add_white > 0; i += 2) {
        for (int j = 0; j < C && add_white > 0; j += 2) {
            grid[i][j] = '.';
            --add_white;
        }
    }

    cout << R << " " << C << "\n";
    for (int i = 0; i < R; ++i) {
        cout << grid[i] << "\n";
    }

    return 0;
}