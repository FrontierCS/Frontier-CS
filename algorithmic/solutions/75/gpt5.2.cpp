#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int b, w, x, y;
    if (!(cin >> b >> w >> x >> y)) return 0;

    int kW = w - 1; // white islands in black area
    int kB = b - 1; // black islands in white area

    int mx = max(kW, kB);
    int c = (mx > 0) ? (2 * mx - 1) : 1;

    vector<string> g;

    // Black base (top)
    if (w > 1) {
        string s(c, '@');
        for (int i = 0; i < kW; i++) s[2 * i] = '.';
        g.push_back(s);              // islands row
        g.push_back(string(c, '@')); // boundary row
    } else {
        g.push_back(string(c, '@')); // only base row
    }

    // White base (bottom)
    if (b > 1) {
        g.push_back(string(c, '.')); // boundary row
        string s(c, '.');
        for (int i = 0; i < kB; i++) s[2 * i] = '@';
        g.push_back(s);              // islands row
    } else {
        g.push_back(string(c, '.')); // only base row
    }

    int r = (int)g.size();
    cout << r << " " << c << "\n";
    for (auto &row : g) cout << row << "\n";
    return 0;
}