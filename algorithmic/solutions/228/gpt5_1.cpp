#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    string s;
    if (!(cin >> s)) {
        cout << 0 << "\n";
        return 0;
    }
    int n = (int)s.size();
    vector<int> pos;
    pos.reserve(n);
    for (int i = 0; i < n; ++i) if (s[i] == '1') pos.push_back(i + 1);
    int m = (int)pos.size();

    // If no ones, no non-empty substring can satisfy zeros = ones^2 (except empty).
    if (m == 0) {
        cout << 0 << "\n";
        return 0;
    }

    // Build D array of distances between consecutive ones and boundaries.
    vector<int> D(m + 2);
    D[1] = pos[0] - 0;
    for (int i = 2; i <= m; ++i) D[i] = pos[i - 1] - pos[i - 2];
    D[m + 1] = (n + 1) - pos[m - 1];

    // Kmax such that k*(k+1) <= n
    long double nd = (long double)n;
    int Kmax = (int)floor((sqrt((long double)1 + 4 * nd) - 1) / 2);
    if (Kmax <= 0) {
        cout << 0 << "\n";
        return 0;
    }

    // Heuristic cap to keep runtime near linear in n
    long double ratio = (long double)(n + 1) / (long double)(m + 1);
    int Kcap = (int)floor(2.0L * ratio + 10.0L);
    if (Kcap > Kmax) Kcap = Kmax;
    if (Kcap < 1) Kcap = 1;

    long long ans = 0;

    // Main loop over starting block of ones index i
    for (int i = 1; i <= m; ++i) {
        int A = D[i];
        int kLimit = m - i + 1;
        if (kLimit > Kcap) kLimit = Kcap;
        // Ensure length constraint implicitly satisfied by Kcap <= Kmax
        int sumD = 0; // sum of D[i+1 .. i+k-1]
        for (int k = 1; k <= kLimit; ++k) {
            int B = D[i + k];
            int g = 1 + sumD;                 // minimal length to include k ones
            int T = k * (k + 1) - g;          // required left+right extension
            int M = (A - 1) + (B - 1);
            if (T >= 0 && T <= M) {
                int low = T - (B - 1);
                if (low < 0) low = 0;
                int hi = T;
                int a1 = A - 1;
                if (hi > a1) hi = a1;
                if (hi >= low) ans += (long long)(hi - low + 1);
            }
            sumD += D[i + k];
        }
    }

    cout << ans << "\n";
    return 0;
}