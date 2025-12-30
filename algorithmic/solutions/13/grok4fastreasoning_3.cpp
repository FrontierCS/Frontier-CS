#include <bits/stdc++.h>

using namespace std;

int main() {
    int sx, sy;
    cin >> sx >> sy;
    vector<pair<int, int>> trap = {
        {sx + 1, 1},
        {sx - 1, 1},
        {sx + 1, 2},
        {sx - 1, 2},
        {sx, 2}
    };
    int i = 0;
    int rx = sx, ry = sy;
    while (i < 3000) {
        int xm, ym;
        if (i < 5) {
            xm = trap[i].first;
            ym = trap[i].second;
        } else {
            xm = rx;
            ym = ry - 1;
        }
        xm = max(1, min(3000, xm));
        ym = max(1, min(3000, ym));
        cout << xm << " " << ym << endl;
        cout.flush();
        int nx, ny;
        cin >> nx >> ny;
        if (nx == 0 && ny == 0) {
            return 0;
        }
        rx = nx;
        ry = ny;
        i++;
    }
    return 0;
}