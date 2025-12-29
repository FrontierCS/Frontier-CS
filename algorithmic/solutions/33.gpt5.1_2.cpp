#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int q;
    if (!(cin >> q)) return 0;
    vector<unsigned long long> k(q);
    for (int i = 0; i < q; ++i) cin >> k[i];

    for (int qi = 0; qi < q; ++qi) {
        unsigned long long T = k[qi] - 1; // K - 1
        vector<char> rev; // operations from last to first

        while (T > 0) {
            if (T & 1ULL) { // odd -> last op was M (T = 2*prev + 1)
                rev.push_back('M');
                T = (T - 1) >> 1;
            } else { // even -> last op was A (T = prev + 1)
                rev.push_back('A');
                --T;
            }
        }

        if (rev.empty()) {
            // This would correspond to k = 1, but constraints say k >= 2.
            cout << 1 << "\n0\n";
            continue;
        }

        // Reverse to get operations in forward order
        vector<char> ops(rev.rbegin(), rev.rend());
        int n = (int)ops.size();

        // Build pseudo-values satisfying:
        // 'M' -> new global max, 'A' -> new global min
        vector<long long> val(n);
        long long curMin = 0, curMax = 0;
        val[0] = 0;
        for (int i = 1; i < n; ++i) {
            if (ops[i] == 'M') {
                val[i] = curMax + 1;
                ++curMax;
            } else { // 'A'
                val[i] = curMin - 1;
                --curMin;
            }
        }

        // Compress pseudo-values to permutation 0..n-1 preserving order
        vector<pair<long long,int>> arr(n);
        for (int i = 0; i < n; ++i) arr[i] = {val[i], i};
        sort(arr.begin(), arr.end());
        vector<int> p(n);
        for (int rank = 0; rank < n; ++rank) {
            p[arr[rank].second] = rank;
        }

        cout << n << "\n";
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << p[i];
        }
        cout << "\n";
    }

    return 0;
}