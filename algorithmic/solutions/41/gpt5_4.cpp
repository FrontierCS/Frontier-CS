#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    unsigned long long n;
    if (!(cin >> n)) return 0;
    
    vector<unsigned long long> ans;
    if (n == 1) {
        cout << 1 << "\n1\n";
        return 0;
    }

    unsigned long long P = 1;
    while (P <= n / 2) P <<= 1; // largest power of two <= n
    unsigned long long Q = P >> 1;

    unsigned long long m = n / Q; // with Q = P/2, m is 2 or 3
    if (m >= 3) {
        if (Q >= 2) {
            // Build 1..S, then P, then R=3Q
            unsigned long long S = Q >> 1;
            for (unsigned long long x = 1; x <= S; x <<= 1) ans.push_back(x);
            ans.push_back(P);
            ans.push_back(Q * m);
        } else {
            // Q == 1 (i.e., P == 2), n must be 3
            ans.push_back(P);
            ans.push_back(Q * m);
        }
    } else {
        // m == 2 -> standard powers of two up to Q, then P
        for (unsigned long long x = 1; x <= Q; x <<= 1) ans.push_back(x);
        ans.push_back(P);
    }

    cout << ans.size() << "\n";
    for (size_t i = 0; i < ans.size(); ++i) {
        if (i) cout << ' ';
        cout << ans[i];
    }
    cout << "\n";
    return 0;
}