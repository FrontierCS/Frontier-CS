#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long h;
    if(!(cin >> h)) return 0;
    long long n = (1LL << h) - 1;
    long long dmax = 2 * h - 2;

    __int128 totalSum = 0;

    for (long long d = 1; d <= dmax; ++d) {
        for (long long u = 1; u <= n; ++u) {
            cout << "? " << u << " " << d << '\n';
            long long x;
            if(!(cin >> x)) return 0;
            totalSum += (__int128)x;
        }
    }

    long long denom = n - 1;
    long long S = (long long)(totalSum / denom);

    cout << "! " << S << '\n';
    cout.flush();
    return 0;
}