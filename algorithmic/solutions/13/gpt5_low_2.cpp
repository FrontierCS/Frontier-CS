#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    const int T = 3000;
    int rx, ry;
    if (!(cin >> rx >> ry)) return 0;

    for (int turn = 1; turn <= T; ++turn) {
        int xm = 1, ym = 1;
        if (1 <= rx && rx <= T && 1 <= ry && ry <= T) {
            xm = rx; ym = ry;
        }
        cout << xm << " " << ym << endl;
        cout.flush();

        int nx, ny;
        if (!(cin >> nx >> ny)) return 0;
        if (nx == 0 && ny == 0) return 0;
        rx = nx; ry = ny;
    }
    return 0;
}