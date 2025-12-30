#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int sx, sy;
    if (!(cin >> sx >> sy)) return 0;
    const int T = 3000;

    for (int t = 1; t <= T; ++t) {
        int x = t, y = 1;
        cout << x << ' ' << y << endl;

        int rx, ry;
        if (!(cin >> rx >> ry)) return 0;
        if (rx == 0 && ry == 0) return 0;
    }
    return 0;
}