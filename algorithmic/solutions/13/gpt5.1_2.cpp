#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int sx, sy;
    if (!(cin >> sx >> sy)) return 0;

    for (int step = 0; step < 3000; ++step) {
        // Always paint (1,1)
        cout << 1 << ' ' << 1 << '\n';
        cout.flush();

        int rx, ry;
        if (!(cin >> rx >> ry)) break;
        if (rx == 0 && ry == 0) break;
    }

    return 0;
}