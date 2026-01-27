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
    vector<int> pref(n + 1, 0);
    for (int i = 0; i < n; ++i) {
        pref[i + 1] = pref[i] + (s[i] == '1');
    }

    auto isqrt = [](long long x)->long long{
        long long r = sqrtl((long double)x);
        while ((r+1)*(r+1) <= x) ++r;
        while (r*r > x) --r;
        return r;
    };

    long long tmax = (isqrt(1 + 4LL * n) - 1) / 2;
    if (tmax <= 0) {
        cout << 0 << "\n";
        return 0;
    }

    const long long OP_BUDGET = 250000000LL; // adjust computation budget
    int T_small = (int)min(tmax, OP_BUDGET / max(1, n));
    if (T_small < 1) T_small = 1;

    int K_tail = (int)min(tmax - T_small, 2000LL);
    int tail_start = (int)(tmax - K_tail + 1);
    if (tail_start <= T_small) tail_start = T_small + 1;

    long long ans = 0;
    const int* base = pref.data();

    // Small t range
    for (int t = 1; t <= T_small; ++t) {
        int L = t * (t + 1);
        if (L > n) break;
        int limit = n - L;
        const int* a = base;
        const int* b = base + L;
        long long cnt = 0;
        for (int i = 0; i <= limit; ++i) {
            cnt += (b[i] - a[i] == t);
        }
        ans += cnt;
    }

    // Tail range near tmax
    for (int t = tail_start; t <= (int)tmax; ++t) {
        int L = t * (t + 1);
        if (L > n) continue;
        int limit = n - L;
        const int* a = base;
        const int* b = base + L;
        long long cnt = 0;
        for (int i = 0; i <= limit; ++i) {
            cnt += (b[i] - a[i] == t);
        }
        ans += cnt;
    }

    cout << ans << "\n";
    return 0;
}