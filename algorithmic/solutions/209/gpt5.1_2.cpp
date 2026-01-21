#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int h;
    if (!(cin >> h)) return 0;
    int n = (1 << h) - 1;
    int D = 2 * h - 2;

    __int128 total = 0;

    for (int u = 1; u <= n; ++u) {
        for (int d = 1; d <= D; ++d) {
            cout << "? " << u << " " << d << endl;
            cout.flush();
            long long ans;
            if (!(cin >> ans)) return 0;
            total += (__int128)ans;
        }
    }

    long long denom = n - 1;
    long long S = (long long)(total / denom);

    cout << "! " << S << endl;
    cout.flush();

    return 0;
}