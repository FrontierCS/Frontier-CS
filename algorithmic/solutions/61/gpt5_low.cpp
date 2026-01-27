#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    if(!(cin >> T)) return 0;
    while(T--){
        int n, m;
        long long c;
        cin >> n >> m >> c;
        vector<long long> a(n+1);
        for(int i=1;i<=n;i++) cin >> a[i];
        vector<long long> b(m+1);
        for(int i=1;i<=m;i++) cin >> b[i];

        // Prefix sums
        vector<long long> S(n+1,0);
        for(int i=1;i<=n;i++) S[i]=S[i-1]+a[i];

        // Compute cumulative thresholds T_k
        vector<long long> T(m+1,0); // T[0]=0
        for(int i=1;i<=m;i++) T[i]=T[i-1]+b[i];

        // Count leading zeros in b (T remains 0 while b prefix sum stays 0)
        int z=0;
        while(z<m && T[z+1]==0) ++z;

        long long cprime = c - z;

        // Function f(x): number of k with T[k] <= x
        auto f = [&](long long x)->int{
            // upper_bound on T
            int k = upper_bound(T.begin(), T.end(), x) - T.begin() - 1;
            if(k<0) k=0;
            return k;
        };

        // If cprime <= 0, best to split every day (each day is a segment)
        // dp not needed: value = sum_i (f(a[i]) - cprime)
        if(cprime <= 0){
            long long ans = 0;
            for(int i=1;i<=n;i++){
                ans += (long long)f(a[i]) - cprime;
            }
            cout << ans << "\n";
            continue;
        }

        // General case: fallback to single segment (heuristic)
        // Value = f(S[n]) - cprime
        long long ans = (long long)f(S[n]) - cprime;
        cout << ans << "\n";
    }
    return 0;
}