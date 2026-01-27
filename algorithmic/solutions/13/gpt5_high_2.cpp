#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int T = 3000;
    int sx, sy;
    if (!(cin >> sx >> sy)) return 0;

    for (int t = 1; t <= T; ++t) {
        int xm = t, ym = 1;
        cout << xm << ' ' << ym << '\n';
        cout.flush();

        int nx, ny;
        if (!(cin >> nx >> ny)) return 0;
        if (nx == 0 && ny == 0) break;
    }
    return 0;
}