#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long b, w, x, y;
    if (!(cin >> b >> w >> x >> y)) return 0;

    const int R = 100, C = 100;
    vector<string> g(R, string(C, '@'));

    // Top half white, bottom half black
    for (int i = 0; i < 50; ++i)
        for (int j = 0; j < C; ++j)
            g[i][j] = '.';

    long long needBlack = b - 1; // additional black components as islands
    long long needWhite = w - 1; // additional white components as islands

    // Place black islands in top half (rows 0..48, even rows and even cols)
    for (int i = 0; i <= 48 && needBlack > 0; i += 2) {
        for (int j = 0; j < C && needBlack > 0; j += 2) {
            g[i][j] = '@';
            --needBlack;
        }
    }

    // Place white islands in bottom half (rows 51..99, odd rows and even cols)
    for (int i = 51; i < R && needWhite > 0; i += 2) {
        for (int j = 0; j < C && needWhite > 0; j += 2) {
            g[i][j] = '.';
            --needWhite;
        }
    }

    cout << R << " " << C << "\n";
    for (int i = 0; i < R; ++i) {
        cout << g[i] << "\n";
    }

    return 0;
}