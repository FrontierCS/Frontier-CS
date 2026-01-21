#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int b, w, x, y;
    if (!(cin >> b >> w >> x >> y)) return 0;

    const int R = 100, C = 100;
    vector<string> g(R, string(C, '@'));

    // Top half '@', bottom half '.'
    for (int i = 0; i < 50; ++i)
        for (int j = 0; j < C; ++j)
            g[i][j] = '@';
    for (int i = 50; i < R; ++i)
        for (int j = 0; j < C; ++j)
            g[i][j] = '.';

    int extraWhite = w - 1; // white islands in top (black) area
    for (int i = 1; i < 49 && extraWhite > 0; i += 2) {
        for (int j = 1; j < 99 && extraWhite > 0; j += 2) {
            g[i][j] = '.';
            --extraWhite;
        }
    }

    int extraBlack = b - 1; // black islands in bottom (white) area
    for (int i = 51; i < 100 && extraBlack > 0; i += 2) {
        for (int j = 1; j < 99 && extraBlack > 0; j += 2) {
            g[i][j] = '@';
            --extraBlack;
        }
    }

    cout << R << " " << C << "\n";
    for (int i = 0; i < R; ++i) {
        cout << g[i] << "\n";
    }

    return 0;
}