#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int h;
    if (!(cin >> h)) return 0;
    int n = (1 << h) - 1;
    int Dmax = 2 * (h - 1); // diameter of perfect binary tree

    __int128 total = 0;

    for (int u = 1; u <= n; ++u) {
        for (int d = 1; d <= Dmax; ++d) {
            cout << "? " << u << " " << d << endl;
            long long ans;
            if (!(cin >> ans)) return 0;
            total += (__int128)ans;
        }
    }

    long long S = (long long)(total / (n - 1));
    cout << "! " << S << endl;
    return 0;
}