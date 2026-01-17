#include <bits/stdc++.h>

using namespace std;

int main() {
    int h;
    cin >> h;
    long long n = (1LL << h) - 1;
    int maxd = 2 * (h - 1);
    __int128 total = 0;
    for (long long u = 1; u <= n; u++) {
        for (int d = 1; d <= maxd; d++) {
            cout << "? " << u << " " << d << endl;
            long long res;
            cin >> res;
            total += res;
        }
    }
    __int128 nn = n - 1;
    __int128 SS = total / nn;
    cout << "! " << (long long) SS << endl;
    return 0;
}