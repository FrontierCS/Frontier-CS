#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int q;
    if (!(cin >> q)) return 0;
    vector<unsigned long long> ks(q);
    for (int i = 0; i < q; ++i) cin >> ks[i];

    for (int qi = 0; qi < q; ++qi) {
        unsigned long long k = ks[qi];
        vector<int> perm; // current permutation values [0..n-1]

        // Operations:
        auto multiply2 = [&]() {
            // append an element with the largest value (n)
            perm.push_back((int)perm.size());
        };
        auto add1 = [&]() {
            // shift all existing values by +1, then append a new element with value 0
            for (int &v : perm) v++;
            perm.push_back(0);
        };

        // Build from binary representation:
        // Start with count c = 1 (empty permutation: perm is empty)
        // For each bit after the highest set bit: c = 2*c + bit
        int msb = 63 - __builtin_clzll(k); // highest bit index
        for (int i = msb - 1; i >= 0; --i) {
            multiply2();
            if ((k >> i) & 1ULL) add1();
        }

        cout << (int)perm.size() << "\n";
        for (int i = 0; i < (int)perm.size(); ++i) {
            if (i) cout << ' ';
            cout << perm[i];
        }
        cout << "\n";
    }
    return 0;
}