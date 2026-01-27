#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int q;
    if(!(cin >> q)) return 0;
    vector<unsigned long long> ks(q);
    for(int i = 0; i < q; ++i) cin >> ks[i];

    for(int i = 0; i < q; ++i) {
        unsigned long long k = ks[i];
        unsigned long long g = k - 1; // non-empty subsequences total
        vector<int> sizes;
        while (g > 0) {
            unsigned long long x = g + 1; // >= 2
            int s = 63 - __builtin_clzll(x); // floor(log2(x))
            unsigned long long d = (1ULL << s) - 1;
            sizes.push_back(s);
            g -= d;
        }
        int n = 0;
        for (int s : sizes) n += s;
        cout << n << "\n";
        vector<int> ans;
        ans.reserve(n);
        int cur = n - 1;
        for (int s : sizes) {
            int start = cur - s + 1;
            for (int v = start; v <= cur; ++v) ans.push_back(v);
            cur = start - 1;
        }
        for (int j = 0; j < n; ++j) {
            if (j) cout << ' ';
            cout << ans[j];
        }
        cout << "\n";
    }
    return 0;
}