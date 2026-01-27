#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    string s;
    if(!(cin >> s)) return 0;
    int n = (int)s.size();
    vector<int> pref(n+1,0);
    for(int i=1;i<=n;i++) pref[i] = pref[i-1] + (s[i-1]=='1');

    if(n <= 1) {
        cout << 0 << '\n';
        return 0;
    }

    long long K = (long long)((sqrtl(1.0L + 4.0L * n) - 1.0L) / 2.0L);
    while((K+1)*(K+2) <= 2LL*(long long)n) { // safeguard adjust
        long long L = (K+1)*(K+2)/2; // not used directly; just increment safely
        (void)L;
        K++;
        if ((K+1)*(K+1)+(K+1) > n) break;
    }
    while(K > 0 && (K*K + K) > n) K--;

    if (K <= 0) {
        cout << 0 << '\n';
        return 0;
    }

    // total number of windows across all k
    long long total_windows = 0;
    for(long long k=1;k<=K;k++){
        long long L = k*k + k;
        total_windows += max(0LL, (long long)n - L + 1);
    }

    const long long MAXCHECK = 50000000LL; // budget of checks
    unsigned long long ans = 0;

    if (total_windows <= MAXCHECK) {
        // exact
        for(long long k=1;k<=K;k++){
            int L = (int)(k*k + k);
            int windows = n - L + 1;
            if (windows <= 0) continue;
            for(int r=L; r<=n; r++){
                if (pref[r] - pref[r-L] == k) ans++;
            }
        }
        cout << ans << '\n';
        return 0;
    }

    // sampling with common stride
    long long stride = (total_windows + MAXCHECK - 1) / MAXCHECK;
    if (stride < 1) stride = 1;

    // deterministic RNG (xorshift64*)
    uint64_t seed = 1469598103934665603ull ^ (uint64_t)n ^ ((uint64_t)pref[n] << 32);
    auto rng = [&]()->uint64_t{
        seed ^= seed >> 12;
        seed ^= seed << 25;
        seed ^= seed >> 27;
        return seed * 2685821657736338717ULL;
    };

    for(long long k=1;k<=K;k++){
        int L = (int)(k*k + k);
        long long windows = (long long)n - L + 1;
        if (windows <= 0) continue;

        if (windows <= stride * 2) {
            // do exact for small windows
            for(int r=L; r<=n; r++){
                if (pref[r] - pref[r-L] == k) ans++;
            }
            continue;
        }

        long long mod = min(stride, windows);
        long long offset = (mod == 0 ? 0 : (rng() % mod));
        long long r0 = L + offset;
        if (r0 > n) r0 = L + (offset % max(1LL, windows));
        long long Sk = ((n - r0) / stride) + 1;
        if (Sk <= 0) continue;

        long long cnt = 0;
        for(long long rr = r0; rr <= n; rr += stride){
            if (pref[(int)rr] - pref[(int)(rr - L)] == k) cnt++;
        }

        long double estimate = (long double)cnt * (long double)windows / (long double)Sk;
        unsigned long long add = (unsigned long long) llround(estimate);
        ans += add;
    }

    cout << ans << '\n';
    return 0;
}