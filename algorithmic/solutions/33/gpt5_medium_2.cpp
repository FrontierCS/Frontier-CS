#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int q;
    if (!(cin >> q)) return 0;
    vector<unsigned long long> ks(q);
    for (int i = 0; i < q; ++i) cin >> ks[i];
    
    for (int i = 0; i < q; ++i) {
        unsigned long long k = ks[i];
        vector<char> ops;
        while (k > 1) {
            if ((k & 1ULL) == 0ULL) {
                ops.push_back('R'); // double
                k >>= 1;
            } else {
                ops.push_back('L'); // +1
                --k;
            }
        }
        reverse(ops.begin(), ops.end());
        
        long long minv = 0, maxv = -1;
        vector<long long> vals;
        vals.reserve(ops.size());
        for (char c : ops) {
            if (c == 'R') {
                ++maxv;
                vals.push_back(maxv);
            } else {
                --minv;
                vals.push_back(minv);
            }
        }
        
        int n = (int)vals.size();
        vector<long long> sorted = vals;
        sort(sorted.begin(), sorted.end());
        sorted.erase(unique(sorted.begin(), sorted.end()), sorted.end());
        
        vector<int> perm(n);
        for (int j = 0; j < n; ++j) {
            int idx = int(lower_bound(sorted.begin(), sorted.end(), vals[j]) - sorted.begin());
            perm[j] = idx;
        }
        
        cout << n << "\n";
        for (int j = 0; j < n; ++j) {
            if (j) cout << ' ';
            cout << perm[j];
        }
        cout << "\n";
    }
    return 0;
}