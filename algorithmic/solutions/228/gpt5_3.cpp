#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    string s;
    if(!(cin >> s)) {
        cout << 0 << "\n";
        return 0;
    }
    int n = (int)s.size();
    vector<int> pref(n+1, 0);
    for (int i = 0; i < n; ++i) pref[i+1] = pref[i] + (s[i] == '1');
    
    long long ans = 0;
    int Kmax = (int)((sqrtl(1.0L + 4.0L*n) - 1.0L) / 2.0L);
    int Ksmall = min(Kmax, 120); // approximate threshold
    
    for (int k = 1; k <= Ksmall; ++k) {
        long long L = 1LL*k*(k+1);
        if (L > n) break;
        int Li = (int)L;
        int limit = n - Li;
        const int *P = pref.data();
        for (int i = 0; i <= limit; ++i) {
            if (P[i+Li] - P[i] == k) ans++;
        }
    }
    
    cout << ans << "\n";
    return 0;
}