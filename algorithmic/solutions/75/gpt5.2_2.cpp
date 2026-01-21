#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int b, w, x, y;
    if (!(cin >> b >> w >> x >> y)) return 0;

    const int R = 100, C = 100;
    vector<string> g(R, string(C, '.'));
    for (int i = 0; i < 50; ++i) g[i].assign(C, '@'); // top half black, bottom half white

    int needW = w - 1; // white islands in black area
    for (int i = 0; i <= 48 && needW > 0; i += 2) {
        for (int j = 0; j < C && needW > 0; j += 2) {
            g[i][j] = '.';
            --needW;
        }
    }

    int needB = b - 1; // black islands in white area
    for (int i = 51; i < R && needB > 0; i += 2) {
        for (int j = 0; j < C && needB > 0; j += 2) {
            g[i][j] = '@';
            --needB;
        }
    }

    cout << R << " " << C << "\n";
    for (auto &row : g) cout << row << "\n";
    return 0;
}