#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    const int T = 3000;
    long long rx, ry;
    if (!(cin >> rx >> ry)) return 0;
    
    for (int t = 1; t <= T; ++t) {
        long long x_m, y_m;
        if (t % 2 == 1) {
            x_m = 1;
            y_m = min<long long>(ry, T);
        } else {
            x_m = min<long long>(rx, T);
            y_m = 1;
        }
        cout << x_m << " " << y_m << endl;
        cout.flush();
        
        long long nx, ny;
        if (!(cin >> nx >> ny)) break;
        if (nx == 0 && ny == 0) break;
        rx = nx; ry = ny;
    }
    return 0;
}