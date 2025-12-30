#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int q;
    if(!(cin >> q)) return 0;
    vector<unsigned long long> ks(q);
    for (int i = 0; i < q; ++i) cin >> ks[i];

    for (int qi = 0; qi < q; ++qi) {
        unsigned long long k = ks[qi];

        // Build sequence of operations: 'L' (largest) and 'S' (smallest)
        // Starting from T=1, for each bit after MSB: T = 2*T; if bit is 1 then T = T + 1.
        vector<char> ops; // 'L' or 'S'
        int msb = 63 - __builtin_clzll(k); // index of highest set bit
        for (int i = msb - 1; i >= 0; --i) {
            ops.push_back('L'); // double
            if ((k >> i) & 1ULL) ops.push_back('S'); // add one
        }

        int n = (int)ops.size();
        cout << n << "\n";
        if (n == 0) {
            cout << "\n";
            continue;
        }

        // Assign relative values for each step: smallest or largest relative to previous
        vector<long long> rel(n);
        long long low = 0, high = -1;
        for (int i = 0; i < n; ++i) {
            if (ops[i] == 'L') {
                high += 1;
                rel[i] = high;
            } else {
                low -= 1;
                rel[i] = low;
            }
        }

        // Compress relative values to a permutation of 0..n-1 by ranking
        vector<int> idx(n);
        iota(idx.begin(), idx.end(), 0);
        sort(idx.begin(), idx.end(), [&](int a, int b){ return rel[a] < rel[b]; });
        vector<int> perm(n);
        for (int rank = 0; rank < n; ++rank) {
            perm[idx[rank]] = rank;
        }

        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << perm[i];
        }
        cout << "\n";
    }
    return 0;
}