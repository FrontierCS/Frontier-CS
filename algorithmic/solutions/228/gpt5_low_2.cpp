#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    string s;
    if(!(cin >> s)) return 0;
    int n = (int)s.size();
    vector<int> pref(n+1,0);
    vector<int> pos;
    pos.reserve(n+2);
    for(int i=0;i<n;i++){
        pref[i+1] = pref[i] + (s[i]=='1');
        if(s[i]=='1') pos.push_back(i+1); // 1-based positions
    }
    long long ans = 0;
    int m = (int)pos.size();
    // Small k via fixed-length window
    int max_k = 0;
    while(1LL*(max_k+1)*(max_k+2) <= 2LL*n) { // rough upper; refine below
        ++max_k;
        if(1LL*max_k*(max_k+1) > n){ --max_k; break; }
    }
    while(1LL*max_k*(max_k+1) > n) --max_k;
    const int B = 100; // threshold for small k
    int smallK = min(B, max_k);
    for(int k=1; k<=smallK; ++k){
        int L = k*(k+1);
        int limit = n - L;
        for(int a=0; a<=limit; ++a){
            if(pref[a+L] - pref[a] == k) ++ans;
        }
    }
    // Large k via ones-block intersection method
    pos.insert(pos.begin(), 0); // pos[0]=0
    pos.push_back(n+1);         // pos[m+1]=n+1
    for(int k=smallK+1; k<=max_k; ++k){
        int L = k*(k+1);
        long long t = (long long)L - 1;
        int upto = m - k + 1;
        for(int i=1; i<=upto; ++i){
            int A = pos[i-1] + 1;
            int Bv = pos[i];
            int C = pos[i+k-1];
            int D = pos[i+k] - 1;
            long long low = max<long long>(A, (long long)C - t);
            long long high = min<long long>(Bv, (long long)D - t);
            if(high >= low) ans += (high - low + 1);
        }
    }
    cout << ans << "\n";
    return 0;
}