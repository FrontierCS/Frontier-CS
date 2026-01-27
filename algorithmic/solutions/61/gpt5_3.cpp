#include <bits/stdc++.h>
using namespace std;

using int64 = long long;

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int T;
    if(!(cin >> T)) return 0;
    while(T--){
        int n, m;
        long long c;
        cin >> n >> m >> c;
        vector<long long> a(n+1), b(m+1);
        for(int i=1;i<=n;i++) cin >> a[i];
        for(int i=1;i<=m;i++) cin >> b[i];
        
        // Prefix sums of a
        vector<long long> P(n+1,0);
        for(int i=1;i<=n;i++) P[i]=P[i-1]+a[i];
        
        // Remove initial zeros in b affecting per-segment free levels
        int zero_prefix = 0;
        while(zero_prefix < m && b[zero_prefix+1]==0) zero_prefix++;
        long long c_adj = c - zero_prefix;
        if(c_adj < 0) c_adj = 0; // handle negative effectively by many segments; but we cap to 0 for this heuristic
        
        // Build thresholds T starting after initial zeros
        vector<long long> Tsum;
        {
            long long s=0;
            for(int i=zero_prefix+1;i<=m;i++){
                s += b[i];
                Tsum.push_back(s);
            }
        }
        int m2 = (int)Tsum.size(); // effective positive thresholds
        // f(S): number of thresholds <= S + zero_prefix
        auto f = [&](long long S)->long long{
            if(S < 0) return 0;
            int k = upper_bound(Tsum.begin(), Tsum.end(), S) - Tsum.begin();
            return (long long)k + zero_prefix;
        };
        
        // DP: dp[i] = max over j<i of dp[j] + f(P[i]-P[j]) - c
        // Heuristic: only consider prefix-record indices to prune dominated (may still be large).
        vector<long long> dp(n+1, LLONG_MIN/4);
        dp[0]=0;
        long long best_pref = dp[0];
        vector<int> records = {0};
        
        for(int i=1;i<=n;i++){
            long long best = LLONG_MIN/4;
            for(int idx = 0; idx < (int)records.size(); idx++){
                int j = records[idx];
                long long val = dp[j] + f(P[i]-P[j]) - c;
                if(val > best) best = val;
            }
            dp[i] = best;
            if(dp[i] > best_pref){
                best_pref = dp[i];
                records.push_back(i);
            }
        }
        
        cout << max(0LL, dp[n]) << "\n";
    }
    return 0;
}