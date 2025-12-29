#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    const int NUM = 1000;
    vector<int> a(NUM), b(NUM), c(NUM), d(NUM);
    for (int i = 0; i < NUM; i++) {
        if (!(cin >> a[i] >> b[i] >> c[i] >> d[i])) return 0;
    }

    int m = 50;
    cout << m;
    for (int i = 0; i < m; i++) {
        cout << " " << (i + 1);
    }
    cout << "\n";

    int n = 2 + 2 * m;
    cout << n;

    // Start at office
    int sx = 400, sy = 400;
    cout << " " << sx << " " << sy;

    // Visit each restaurant then its destination
    for (int i = 0; i < m; i++) {
        cout << " " << a[i] << " " << b[i];
        cout << " " << c[i] << " " << d[i];
    }

    // Return to office
    cout << " " << sx << " " << sy << "\n";

    return 0;
}