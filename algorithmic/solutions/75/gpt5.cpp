#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int b, w, x, y;
    if(!(cin >> b >> w >> x >> y)) return 0;

    const int R = 100, C = 100;
    vector<string> g(R, string(C, '@'));

    // Bottom half white
    for (int i = 50; i < R; ++i) {
        for (int j = 0; j < C; ++j) g[i][j] = '.';
    }

    // Place white islands in top black half (not touching the border with white half)
    int needW = w - 1;
    for (int i = 0; i < 49 && needW > 0; i += 2) {
        for (int j = 0; j < C && needW > 0; j += 2) {
            g[i][j] = '.';
            --needW;
        }
    }

    // Place black islands in bottom white half (not touching the border with black half)
    int needB = b - 1;
    for (int i = 51; i < R && needB > 0; i += 2) {
        for (int j = 0; j < C && needB > 0; j += 2) {
            g[i][j] = '@';
            --needB;
        }
    }

    cout << R << " " << C << "\n";
    for (int i = 0; i < R; ++i) cout << g[i] << "\n";
    return 0;
}