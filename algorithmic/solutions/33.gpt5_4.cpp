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
        unsigned long long x = k - 1; // represent k-1 as sum of powers of two
        vector<int> bits;
        int r = 0;
        while (x) {
            if (x & 1ULL) bits.push_back(r);
            x >>= 1ULL;
            ++r;
        }
        // If k-1 == 0, there are no set bits; but k >= 2 by constraints, so bits non-empty.
        long long n = 0;
        for (int b : bits) n += (b + 1);
        cout << n << "\n";
        if (n == 0) {
            cout << "\n";
            continue;
        }
        vector<long long> res;
        res.reserve(n);
        long long curVal = n - 1;
        // Build each piece: increasing run of length r, then one small element, ensuring all values
        // in earlier pieces are greater than later pieces.
        for (int b : bits) {
            long long L = b + 1;
            long long v0 = curVal - b; // smallest value in this piece (for the trailing single element)
            // A: increasing sequence of length b with values v0+1..curVal
            for (long long v = v0 + 1; v <= curVal; ++v) res.push_back(v);
            // B: single element v0
            res.push_back(v0);
            curVal = v0 - 1;
        }
        for (size_t j = 0; j < res.size(); ++j) {
            if (j) cout << ' ';
            cout << res[j];
        }
        cout << "\n";
    }

    return 0;
}