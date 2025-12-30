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
        unsigned long long k = ks[qi]; // k >= 2
        vector<long long> arr;
        long long low = -1, high = 0;

        // Start with single element (F = 2)
        arr.push_back(0);

        int msb = 63 - __builtin_clzll(k); // floor(log2(k))
        for (int i = msb - 1; i >= 0; --i) {
            if ((k >> i) & 1ULL) {
                arr.push_back(low--); // +1 operation: append smallest
            }
            if (i != 0) {
                arr.push_back(++high); // *2 operation: append largest
            }
        }

        int n = (int)arr.size();
        vector<pair<long long,int>> vp(n);
        for (int i = 0; i < n; ++i) vp[i] = {arr[i], i};
        sort(vp.begin(), vp.end());
        vector<int> perm(n);
        for (int rank = 0; rank < n; ++rank) {
            perm[vp[rank].second] = rank;
        }

        cout << n << "\n";
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << perm[i];
        }
        cout << "\n";
    }

    return 0;
}