#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int h;
    if (!(cin >> h)) return 0;
    long long n = (1LL << h) - 1;
    int D = 2 * (h - 1);

    __int128 total = 0;
    for (int d = 1; d <= D; ++d) {
        for (long long u = 1; u <= n; ++u) {
            cout << "? " << u << " " << d << endl;
            long long x;
            if (!(cin >> x)) return 0;
            total += (__int128)x;
        }
    }

    long long S = (long long)(total / (n - 1));
    cout << "! " << S << endl;
    return 0;
}