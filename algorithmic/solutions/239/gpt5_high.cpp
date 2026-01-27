#include <bits/stdc++.h>
using namespace std;

long long computeM(int n, int k1, int k2) {
    long long res = 0;
    int rmax = min(n, k1 - 1);
    if (rmax >= 2) {
        long long cnt = 1LL * (n + 1) * (rmax - 1) - (1LL * rmax * (rmax + 1) / 2 - 1);
        res += cnt;
    }
    if (k1 > 0) {
        int jmax = min(k2 - 1, n / k1);
        if (jmax >= 1) {
            long long cnt = 1LL * jmax * (n + 1) - 1LL * k1 * (1LL * jmax * (jmax + 1) / 2);
            res += cnt;
        }
    }
    long long g = 1LL * k1 * k2;
    if (g > 0) {
        int imax = n / g;
        if (imax >= 1) {
            long long cnt = 1LL * imax * (n + 1) - g * (1LL * imax * (imax + 1) / 2);
            res += cnt;
        }
    }
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if (!(cin >> n)) return 0;

    if (n <= 3) {
        cout << 0 << "\n";
        return 0;
    }

    int lim = min(n, 256);
    int best1 = 2, best2 = 2;
    long long bestM = LLONG_MAX;

    for (int k1 = 2; k1 <= lim; ++k1) {
        for (int k2 = 2; k2 <= lim; ++k2) {
            long long m = computeM(n, k1, k2);
            if (m < bestM) {
                bestM = m;
                best1 = k1;
                best2 = k2;
            }
        }
    }

    cout << bestM << "\n";

    int k1 = best1, k2 = best2;

    // Stage 1: lengths r = 2..k1-1
    for (int r = 2; r <= k1 - 1 && r <= n; ++r) {
        for (int s = 0; s + r <= n; ++s) {
            cout << s << " " << (s + r - 1) << " " << (s + r) << "\n";
        }
    }

    // Stage 2: multiples of k1, j = 1..min(k2-1, n/k1)
    int jmax = min(k2 - 1, n / k1);
    for (int j = 1; j <= jmax; ++j) {
        int L = j * k1;
        int A = (j == 1 ? k1 - 1 : (j - 1) * k1);
        for (int s = 0; s + L <= n; ++s) {
            cout << s << " " << (s + A) << " " << (s + L) << "\n";
        }
    }

    // Stage 3: multiples of g = k1*k2, i = 1..floor(n/g)
    long long g = 1LL * k1 * k2;
    int imax = n / g;
    for (int i = 1; i <= imax; ++i) {
        long long L = 1LL * i * g;
        long long A = (i == 1 ? 1LL * (k2 - 1) * k1 : 1LL * (i - 1) * g);
        for (int s = 0; s + L <= n; ++s) {
            cout << s << " " << (s + A) << " " << (s + L) << "\n";
        }
    }

    return 0;
}