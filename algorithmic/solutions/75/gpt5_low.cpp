#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int b, w, x, y;
    if (!(cin >> b >> w >> x >> y)) return 0;

    const int H = 50;
    const int W = 100;
    int R = 2 * H + 1;
    int C = W;

    vector<string> grid(R, string(C, '.'));

    // Decide separator color to minimize cost: give the extra row to cheaper color
    char sep = (x <= y) ? '@' : '.';

    // Initialize backgrounds
    // Top block: white ('.')
    for (int i = 0; i < H; ++i) {
        for (int j = 0; j < C; ++j) grid[i][j] = '.';
    }
    // Separator row
    for (int j = 0; j < C; ++j) grid[H][j] = sep;
    // Bottom block: black ('@')
    for (int i = H + 1; i < R; ++i) {
        for (int j = 0; j < C; ++j) grid[i][j] = '@';
    }

    // Place black islands in the top white block: need (b - 1)
    int needBlack = b - 1;
    for (int i = 0; i < H && needBlack > 0; ++i) {
        if (sep == '@' && i == H - 1) continue; // avoid touching separator of same color
        if (i % 2 == 1) {
            for (int j = 1; j < C && needBlack > 0; j += 2) {
                grid[i][j] = '@';
                --needBlack;
            }
        }
    }

    // Place white islands in the bottom black block: need (w - 1)
    int needWhite = w - 1;
    for (int i = H + 1; i < R && needWhite > 0; ++i) {
        if (sep == '.' && i == H + 1) continue; // avoid touching separator of same color
        if (i % 2 == 1) {
            for (int j = 1; j < C && needWhite > 0; j += 2) {
                grid[i][j] = '.';
                --needWhite;
            }
        }
    }

    cout << R << " " << C << "\n";
    for (int i = 0; i < R; ++i) {
        cout << grid[i] << "\n";
    }

    return 0;
}