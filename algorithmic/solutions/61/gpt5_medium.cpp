#include <bits/stdc++.h>
using namespace std;

using int64 = long long;

int main() {
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
        // prefix sums of a
        vector<long long> P(n+1,0);
        for(int i=1;i<=n;i++) P[i]=P[i-1]+a[i];
        // prefix sums of b (thresholds S_k)
        vector<long long> S(m+1,0);
        for(int i=1;i<=m;i++) S[i]=S[i-1]+b[i];
        auto L_of = [&](long long x)->int{
            if(x < 0) return -1000000000; // never used in max
            int k = upper_bound(S.begin(), S.end(), x) - S.begin();
            if(k > m) k = m;
            return k;
        };

        const long long NEG = -(1LL<<60);
        vector<long long> dp(n+1, NEG);
        vector<long long> prefMax(n+1, NEG);
        dp[0]=0;
        prefMax[0]=0;
        for(int i=1;i<=n;i++){
            long long best = NEG;
            for(int r=0;r<=i-1;r++){
                int lv = L_of(P[i]-P[r]);
                long long val = prefMax[r] + lv - c;
                if(val > best) best = val;
            }
            dp[i]=best;
            prefMax[i]=max(prefMax[i-1], dp[i]);
        }
        cout << prefMax[n] << "\n";
    }
    return 0;
}