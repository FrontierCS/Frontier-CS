#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int b, w, x, y;
    if(!(cin >> b >> w >> x >> y)) return 0;

    const int T = 50; // half height
    int need = max(b - 1, w - 1);
    int K = (need + 25 - 1) / 25; // ceil(need/25)
    int c = (K == 0 ? 1 : 2 * K - 1);
    int r = 2 * T; // 100

    vector<string> grid(r, string(c, '.'));
    // Top half white '.', bottom half black '@'
    for (int i = T; i < r; ++i) {
        for (int j = 0; j < c; ++j) grid[i][j] = '@';
    }

    int needBlackIslands = b - 1;
    int needWhiteIslands = w - 1;

    // Place black islands in the top (white) half at even rows/cols, avoiding row T-1 (49)
    for (int i = 0; i <= T - 2 && needBlackIslands > 0; i += 2) {
        for (int j = 0; j < c && needBlackIslands > 0; j += 2) {
            grid[i][j] = '@';
            --needBlackIslands;
        }
    }

    // Place white islands in the bottom (black) half at odd rows starting from T+1 (51), even cols
    for (int i = T + 1; i < r && needWhiteIslands > 0; i += 2) {
        for (int j = 0; j < c && needWhiteIslands > 0; j += 2) {
            grid[i][j] = '.';
            --needWhiteIslands;
        }
    }

    cout << r << " " << c << "\n";
    for (int i = 0; i < r; ++i) {
        cout << grid[i] << "\n";
    }
    return 0;
}