#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int q;
    if(!(cin >> q)) return 0;
    vector<unsigned long long> ks(q);
    for (int i = 0; i < q; ++i) cin >> ks[i];

    for (int i = 0; i < q; ++i) {
        unsigned long long k = ks[i];
        unsigned long long rem = k - 1; // represent as sum of (2^l - 1)
        vector<int> lens;
        while (rem > 0) {
            unsigned long long x = rem + 1;
            int l = 63 - __builtin_clzll(x); // floor(log2(rem+1))
            if (l == 0) l = 1;
            unsigned long long coin = (1ULL << l) - 1;
            lens.push_back(l);
            rem -= coin;
        }
        int n = 0;
        for (int l : lens) n += l;
        cout << n << "\n";
        vector<int> p;
        p.reserve(n);
        int cur = n - 1;
        for (int l : lens) {
            for (int v = cur - l + 1; v <= cur; ++v) p.push_back(v);
            cur -= l;
        }
        for (int j = 0; j < n; ++j) {
            if (j) cout << ' ';
            cout << p[j];
        }
        cout << "\n";
    }
    return 0;
}