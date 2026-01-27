#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int sx, sy;
    if (!(cin >> sx >> sy)) return 0;

    const int T = 3000;
    for (int t = 1; t <= T; ++t) {
        // Always mark (1,1), which is within [1..T] x [1..T]
        cout << 1 << " " << 1 << endl;
        cout.flush();

        int nx, ny;
        if (!(cin >> nx >> ny)) return 0;
        if (nx == 0 && ny == 0) break;
    }

    return 0;
}