#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int b, w, x, y;
    if (!(cin >> b >> w >> x >> y)) return 0;

    const int R = 100;
    const int C = 100;
    vector<string> g(R, string(C, '.'));

    // Initialize: top half white '.', bottom half black '@'
    for (int i = 0; i < R; ++i) {
        char ch = (i < R / 2) ? '.' : '@';
        for (int j = 0; j < C; ++j) {
            g[i][j] = ch;
        }
    }

    // Add additional black components in the white (top) half
    int needB = b - 1;
    for (int i = 0; i < R / 2 - 1 && needB > 0; i += 2) { // rows 0..48 (even indices)
        for (int j = 0; j < C && needB > 0; j += 2) {     // cols 0..98 (even indices)
            g[i][j] = '@';
            --needB;
        }
    }

    // Add additional white components in the black (bottom) half
    int needW = w - 1;
    for (int i = R / 2 + 1; i < R && needW > 0; i += 2) { // rows 51..99 (odd indices)
        for (int j = 0; j < C && needW > 0; j += 2) {     // cols 0..98 (even indices)
            g[i][j] = '.';
            --needW;
        }
    }

    cout << R << ' ' << C << "\n";
    for (int i = 0; i < R; ++i) {
        cout << g[i] << "\n";
    }

    return 0;
}