#include <bits/stdc++.h>
using namespace std;

#ifdef _WIN32
#define getchar_unlocked getchar
#endif

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    // Fast read of a single 01-string line
    vector<unsigned char> s;
    s.reserve(2000005);
    int c;
    while ((c = getchar_unlocked()) != EOF) {
        if (c == '0' || c == '1') {
            s.push_back((unsigned char)c);
        } else if (c == '\n') {
            break;
        }
    }
    int n = (int)s.size();
    if (n == 0) { 
        cout << 0 << '\n';
        return 0; 
    }

    // Build prefix sums of ones
    vector<int> pref(n + 1);
    pref[0] = 0;
    for (int i = 0; i < n; ++i) {
        pref[i + 1] = pref[i] + (s[i] == '1');
    }
    int onesTotal = pref[n];
    int zerosTotal = n - onesTotal;

    // Determine Kmax: k such that k^2 + k <= n, k <= onesTotal, k^2 <= zerosTotal
    auto kmax_len = (int)((sqrtl(1.0L + 4.0L * n) - 1.0L) / 2.0L);
    while ((long long)kmax_len * (kmax_len + 1) > n) --kmax_len;
    while ((long long)(kmax_len + 1) * (kmax_len + 2) <= n) ++kmax_len;

    int kmax_zero = (int)(sqrtl((long double)zerosTotal));
    while ((long long)kmax_zero * kmax_zero > zerosTotal) --kmax_zero;
    while ((long long)(kmax_zero + 1) * (kmax_zero + 1) <= zerosTotal) ++kmax_zero;

    int Kmax = min(kmax_len, min(onesTotal, kmax_zero));
    if (Kmax <= 0) {
        cout << 0 << '\n';
        return 0;
    }

    long long ans = 0;

    // For each k, count substrings of length t = k^2 + k having exactly k ones
    for (int k = 1; k <= Kmax; ++k) {
        int t = k * k + k;
        if (t > n) break;
        int N = n - t; // last starting index is N
        int *p = pref.data();
        int *q = pref.data() + t;
        int i = 0;
        int limit = N + 1;
        // Unroll by 4 for speed
        for (; i + 4 <= limit; i += 4) {
            ans += (q[i] - p[i] == k);
            ans += (q[i + 1] - p[i + 1] == k);
            ans += (q[i + 2] - p[i + 2] == k);
            ans += (q[i + 3] - p[i + 3] == k);
        }
        for (; i < limit; ++i) {
            ans += (q[i] - p[i] == k);
        }
    }

    cout << ans << '\n';
    return 0;
}