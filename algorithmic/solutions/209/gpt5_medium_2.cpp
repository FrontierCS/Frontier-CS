#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int h;
    if(!(cin >> h)) return 0;
    long long n = (1LL << h) - 1;
    int H = h - 1;
    int D = 2 * H;

    __int128 total_q = 0;
    unsigned long long rem_sum = 0;
    long long denom = n - 1;

    for (long long u = 1; u <= n; ++u) {
        unsigned long long per = 0;
        for (int d = 1; d <= D; ++d) {
            cout << "? " << u << " " << d << "\n";
            cout.flush();
            long long x;
            if(!(cin >> x)) return 0;
            per += (unsigned long long)x;
        }
        total_q += (per / (unsigned long long)denom);
        rem_sum += (per % (unsigned long long)denom);
        if (rem_sum >= (unsigned long long)denom) {
            total_q += rem_sum / (unsigned long long)denom;
            rem_sum %= (unsigned long long)denom;
        }
    }
    // Final carry from remainders
    total_q += rem_sum / (unsigned long long)denom;

    unsigned long long S = (unsigned long long)total_q;
    cout << "! " << S << "\n";
    cout.flush();
    return 0;
}