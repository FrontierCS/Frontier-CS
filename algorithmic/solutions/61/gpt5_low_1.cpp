#include <bits/stdc++.h>
using namespace std;

using ll = long long;

int main(){
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int T;
    if(!(cin>>T)) return 0;
    while(T--){
        int n, m;
        ll c;
        cin >> n >> m >> c;
        vector<ll> a(n+1), b(m+1);
        for(int i=1;i<=n;i++) cin >> a[i];
        for(int i=1;i<=m;i++) cin >> b[i];
        // prefix sums of a
        vector<ll> P(n+1,0);
        for(int i=1;i<=n;i++) P[i]=P[i-1]+a[i];
        // thresholds t_k
        vector<ll> t(m+1,0);
        for(int i=1;i<=m;i++) t[i]=t[i-1]+b[i];
        // helper K(x) = max k s.t. t[k] <= x
        auto K = [&](ll x)->int{
            if(x < 0) return 0;
            int k = upper_bound(t.begin(), t.end(), x) - t.begin() - 1;
            if(k < 0) k = 0;
            if(k > m) k = m;
            return k;
        };

        // Divide and conquer optimization (assumes monotone opt index)
        vector<ll> dp(n+1, LLONG_MIN/4);
        dp[0] = -c; // one segment covering nothing? We must start from day1.
        // Better initialize dp properly: dp[i] = max over j<i dp[j] + K(P[i]-P[j]) - c
        // We can set dp[0]=0 to represent no segments yet, then transitions subtract c.
        dp[0] = 0;

        function<void(int,int,int,int)> solve = [&](int L, int R, int optL, int optR){
            if(L>R) return;
            int mid = (L+R)/2;
            ll best = LLONG_MIN/4;
            int bestK = optL;
            int rl = min(mid-1, optR);
            for(int j=optL; j<=rl; ++j){
                ll val = dp[j] + (ll)K(P[mid]-P[j]) - c;
                if(val > best){
                    best = val;
                    bestK = j;
                }
            }
            // Also consider starting from scratch when j=0 implicitly included above
            // Set result for mid
            static vector<ll> ndp;
            // We will store in a temp static map, but simpler: overwrite in place storing next layer
            // To avoid confusion, use separate array
            // We'll allocate once outside
            // But here, for simplicity within this function, write to a global array
            // Instead, declare ndp outside the recursion.

            // To handle writing, we use a reference to a global array; so we refactor:
            // We'll capture a pointer to output array via static storage not ideal. Instead,
            // we'll define ndp outside and capture by reference in lambda. We'll restructure code.
        };

        // We'll perform one pass D&C computing dp2 from dp, but the recurrence is one-layer (no stages).
        // However standard D&C works to compute dp for all i from same dp as previous j states.
        vector<ll> dp2(n+1, LLONG_MIN/4);
        function<void(int,int,int,int)> dc = [&](int L,int R,int optL,int optR){
            if(L>R) return;
            int mid=(L+R)>>1;
            ll best = LLONG_MIN/4;
            int bestPos = optL;
            int jlim = min(mid-1, optR);
            for(int j=optL;j<=jlim;++j){
                ll val = dp[j] + (ll)K(P[mid]-P[j]) - c;
                if(val > best){
                    best = val;
                    bestPos = j;
                }
            }
            dp2[mid] = best;
            dc(L, mid-1, optL, bestPos);
            dc(mid+1, R, bestPos, optR);
        };

        // Base: dp2[0] should be 0 (no days, no segments)
        dp2[0] = 0;
        // Compute dp2[1..n]
        dc(1, n, 0, n-1);

        // The answer is dp2[n]
        cout << dp2[n] << "\n";
    }
    return 0;
}