#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long h;
    if (!(cin >> h)) return 0;
    long long n = (1LL << h) - 1;
    long long D = 2 * (h - 1);

    long long total = 0;
    for (long long u = 1; u <= n; ++u) {
        for (long long d = 1; d <= D; ++d) {
            cout << "? " << u << " " << d << endl;
            long long ans;
            if (!(cin >> ans)) return 0;
            total += ans;
        }
    }
    long long S = (n > 1) ? (total / (n - 1)) : 0;
    cout << "! " << S << endl;
    return 0;
}