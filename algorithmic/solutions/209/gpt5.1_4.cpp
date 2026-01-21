#include <bits/stdc++.h>
using namespace std;
using int64 = long long;
using i128 = __int128_t;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int h;
    if (!(cin >> h)) return 0;

    int n = (1 << h) - 1;
    int Dmax = 2 * (h - 1);

    vector<i128> B(Dmax + 1, 0);

    for (int u = 1; u <= n; ++u) {
        for (int d = 1; d <= Dmax; ++d) {
            cout << "? " << u << " " << d << endl;
            long long ans;
            if (!(cin >> ans)) return 0;
            B[d] += (i128)ans;
        }
    }

    i128 T = 0;
    for (int d = 1; d <= Dmax; ++d) {
        T += B[d];
    }

    i128 denom = n - 1;
    i128 S128 = T / denom;
    long long S = (long long)S128;

    cout << "! " << S << endl;

    return 0;
}