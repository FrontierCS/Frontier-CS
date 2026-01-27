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
        vector<long long> a(n+1), b(m+1);
        for(int i=1;i<=n;i++) cin >> a[i];
        for(int i=1;i<=m;i++) cin >> b[i];
        vector<long long> A(n+1,0), B(m+1,0);
        for(int i=1;i<=n;i++) A[i]=A[i-1]+a[i];
        for(int i=1;i<=m;i++) B[i]=B[i-1]+b[i];

        // Fallback trivial lower bound: single segment
        long long ans = upper_bound(B.begin(), B.end(), A[n]) - B.begin() - 1; // index k s.t. B[k] <= A[n]
        cout << (ans - c) << "\n";
    }
    return 0;
}