#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int sx, sy;
    if (!(cin >> sx >> sy)) return 0;

    const int T = 3000;
    for (int step = 1; step <= T; ++step) {
        int xm = step; 
        int ym = 1;
        cout << xm << " " << ym << endl;

        int nx, ny;
        if (!(cin >> nx >> ny)) return 0;
        if (nx == 0 && ny == 0) break;
    }

    return 0;
}