#include <bits/stdc++.h>
using namespace std;

static vector<int> buildPermutation(unsigned long long k) {
    vector<int> bits;
    while (k > 0) {
        bits.push_back(int(k & 1ULL));
        k >>= 1ULL;
    }
    reverse(bits.begin(), bits.end()); // MSB -> LSB

    long long lo = 0, hi = 0;
    vector<long long> vals;
    // Skip MSB (always 1). Start from the next bit.
    for (size_t i = 1; i < bits.size(); i++) {
        // Multiply by 2: append new maximum
        ++hi;
        vals.push_back(hi);
        // Add bit: if 1, append new minimum
        if (bits[i] == 1) {
            --lo;
            vals.push_back(lo);
        }
    }

    vector<long long> sorted = vals;
    sort(sorted.begin(), sorted.end());
    // vals are unique by construction; no need to unique().

    vector<int> perm;
    perm.reserve(vals.size());
    for (long long x : vals) {
        int r = int(lower_bound(sorted.begin(), sorted.end(), x) - sorted.begin());
        perm.push_back(r);
    }
    return perm;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int q;
    cin >> q;
    for (int i = 0; i < q; i++) {
        unsigned long long k;
        cin >> k;
        vector<int> p = buildPermutation(k);
        cout << p.size() << "\n";
        for (size_t j = 0; j < p.size(); j++) {
            if (j) cout << ' ';
            cout << p[j];
        }
        cout << "\n";
    }
    return 0;
}