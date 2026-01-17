#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    long long n;
    long long x, y;
    if (!(cin >> n >> x >> y)) return 0;
    
    if (x > y) swap(x, y); // ensure x <= y
    
    // Case: no constraints active
    if (x > n - 1 && y > n - 1) {
        cout << n << '\n';
        return 0;
    }
    
    // Handle cases that effectively reduce to a single forbidden difference
    if (x == y || x > n - 1 || y > n - 1) {
        long long d;
        if (x == y) d = x;
        else if (x > n - 1) d = y;
        else d = x; // y > n-1
        
        // Single difference d with d <= n-1
        long long q = n / d;
        long long r = n % d;
        long long val1 = (q + 1) / 2; // ceil(q / 2)
        long long val2 = (q + 2) / 2; // ceil((q + 1) / 2)
        long long ans = r * val2 + (d - r) * val1;
        cout << ans << '\n';
        return 0;
    }
    
    // General two-difference case
    const long long LIMIT = 20000000LL; // 20M, >= max(x,y)=2^22
    
    auto greedy_interval = [&](long long L, long long burn_in, long long dx, long long dy) -> long long {
        vector<char> take(L + 1, 0); // 1-based
        long long cnt = 0, pref = 0;
        for (long long i = 1; i <= L; ++i) {
            bool ok = true;
            if (i > dx && take[i - dx]) ok = false;
            if (i > dy && take[i - dy]) ok = false;
            if (ok) {
                take[i] = 1;
                ++cnt;
                if (i <= burn_in) ++pref;
            }
        }
        if (L <= burn_in) return cnt; // full count if no suffix
        // We return total, but caller will use (cnt - pref) / (L - burn_in) for density
        // For exact small-n usage, burn_in should be 0.
        // Here we just return cnt; prefix info is used separately when needed.
        return (cnt << 32) | pref; // pack cnt and pref in 64 bits
    };
    
    if (n <= LIMIT) {
        // Use greedy directly on full interval (approximate but exact for our heuristic)
        long long L = n;
        vector<char> take(L + 1, 0);
        long long cnt = 0;
        for (long long i = 1; i <= L; ++i) {
            bool ok = true;
            if (i > x && take[i - x]) ok = false;
            if (i > y && take[i - y]) ok = false;
            if (ok) {
                take[i] = 1;
                ++cnt;
            }
        }
        cout << cnt << '\n';
        return 0;
    } else {
        // Sample a large prefix and estimate density from its suffix to reduce boundary effects
        long long L = LIMIT;
        long long D = y; // max(x,y) since x <= y
        long long burn = min(L / 2, 5 * D); // burn-in length
        
        vector<char> take(L + 1, 0);
        long long cnt = 0, pref = 0;
        for (long long i = 1; i <= L; ++i) {
            bool ok = true;
            if (i > x && take[i - x]) ok = false;
            if (i > y && take[i - y]) ok = false;
            if (ok) {
                take[i] = 1;
                ++cnt;
                if (i <= burn) ++pref;
            }
        }
        
        long double density;
        if (L > burn) density = (long double)(cnt - pref) / (long double)(L - burn);
        else density = (long double)cnt / (long double)L;
        
        long long ans = (long long) llround(density * (long double)n);
        cout << ans << '\n';
    }
    
    return 0;
}