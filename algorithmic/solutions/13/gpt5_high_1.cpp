#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int sx, sy;
    if (!(cin >> sx >> sy)) return 0;
    
    const int T = 3000;
    for (int t = 0; t < T; ++t) {
        cout << 1 << " " << 1 << endl; // flush each move
        int nx, ny;
        if (!(cin >> nx >> ny)) return 0;
        if (nx == 0 && ny == 0) return 0;
    }
    return 0;
}