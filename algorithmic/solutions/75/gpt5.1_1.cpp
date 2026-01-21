#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int b, w, x, y;
    if (!(cin >> b >> w >> x >> y)) return 0;

    const int R = 100;
    const int C = 100;

    vector<string> g(R, string(C, '@'));
    for (int i = 50; i < R; ++i) {
        g[i] = string(C, '.');
    }

    int needWhiteExtra = w - 1;
    int needBlackExtra = b - 1;

    // Place white islands in the upper (black) half
    for (int i = 1; i < 49 && needWhiteExtra > 0; i += 2) {
        for (int j = 1; j < C && needWhiteExtra > 0; j += 2) {
            g[i][j] = '.';
            --needWhiteExtra;
        }
    }

    // Place black islands in the lower (white) half
    for (int i = 51; i < R && needBlackExtra > 0; i += 2) {
        for (int j = 1; j < C && needBlackExtra > 0; j += 2) {
            g[i][j] = '@';
            --needBlackExtra;
        }
    }

    cout << R << " " << C << "\n";
    for (int i = 0; i < R; ++i) {
        cout << g[i] << "\n";
    }

    return 0;
}