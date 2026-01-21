#include <bits/stdc++.h>
using namespace std;

using int64 = long long;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int T;
    if(!(cin >> T)) return 0;
    while (T--) {
        int n, m;
        long long c;
        cin >> n >> m >> c;
        vector<long long> a(n+1,0), b(m+1,0);
        for (int i = 1; i <= n; ++i) cin >> a[i];
        for (int i = 1; i <= m; ++i) cin >> b[i];
        // Build prefix sums of b
        vector<long long> B(m+1, 0);
        for (int i = 1; i <= m; ++i) B[i] = B[i-1] + b[i];
        
        auto f = [&](long long S)->long long {
            // largest k in [0..m] with B[k] <= S
            int k = int(upper_bound(B.begin(), B.end(), S) - B.begin()) - 1;
            if (k < 0) k = 0;
            if (k > m) k = m;
            return k;
        };
        
        long long res = 0;
        bool started = false;
        long long S = 0; // current segment sum
        for (int i = 1; i <= n; ++i) {
            if (!started) {
                res += f(a[i]) - c;
                S = a[i];
                started = true;
            } else {
                long long contInc = f(S + a[i]) - f(S);
                long long newInc = f(a[i]) - c;
                if (newInc > contInc) {
                    res += newInc;
                    S = a[i];
                } else {
                    res += contInc;
                    S += a[i];
                }
            }
        }
        cout << res << "\n";
    }
    return 0;
}