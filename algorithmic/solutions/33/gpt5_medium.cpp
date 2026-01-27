#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int q;
    if(!(cin >> q)) return 0;
    vector<unsigned long long> ks(q);
    for(int i = 0; i < q; ++i) cin >> ks[i];
    
    for(int qi = 0; qi < q; ++qi){
        unsigned long long k = ks[qi];
        unsigned long long x = k - 1; // sum of 2^p over set bits
        vector<int> sizes;
        int pos = 0;
        while (x) {
            if (x & 1ULL) sizes.push_back(pos + 1); // block size = p+1
            x >>= 1ULL;
            ++pos;
        }
        if (k == 1) { // not expected per constraints, but handle defensively
            cout << 0 << "\n\n";
            continue;
        }
        if (sizes.empty()) { // k == 1? but constraints say k >= 2
            sizes.push_back(1);
        }
        
        // Total length
        int n = 0;
        for (int s : sizes) n += s;
        
        vector<int> perm;
        perm.reserve(n);
        
        int cur = n - 1;
        // Process blocks in any order; we'll use descending sizes for determinism
        // though order doesn't matter for correctness.
        for (int i = (int)sizes.size() - 1; i >= 0; --i) {
            int s = sizes[i];
            // Values allocated to this block: cur - s + 1 ... cur
            vector<int> vals(s);
            for (int j = 0; j < s; ++j) vals[j] = cur - s + 1 + j; // ascending
            // Place first s-1 elements as increasing (vals[1..s-1]),
            // then the last element as the smallest (vals[0]).
            for (int j = 1; j < s; ++j) perm.push_back(vals[j]);
            perm.push_back(vals[0]);
            cur -= s;
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