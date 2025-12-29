#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int q;
    cin >> q;
    while (q--) {
        unsigned long long k;
        cin >> k;

        vector<int> bits;
        {
            unsigned long long x = k;
            while (x) {
                bits.push_back(int(x & 1ULL));
                x >>= 1ULL;
            }
            reverse(bits.begin(), bits.end());
        }

        vector<long long> seq;
        long long low = 0, high = -1;

        // Start with count = 1 (empty permutation)
        // For each next bit b: count = 2*count + b
        for (size_t i = 1; i < bits.size(); i++) {
            // multiply by 2: append new maximum
            high++;
            seq.push_back(high);

            // add 1 if bit is 1: append new minimum
            if (bits[i] == 1) {
                low--;
                seq.push_back(low);
            }
        }

        int n = (int)seq.size();
        vector<long long> sorted = seq;
        sort(sorted.begin(), sorted.end());
        sorted.erase(unique(sorted.begin(), sorted.end()), sorted.end());

        vector<int> perm(n);
        for (int i = 0; i < n; i++) {
            perm[i] = (int)(lower_bound(sorted.begin(), sorted.end(), seq[i]) - sorted.begin());
        }

        cout << n << "\n";
        for (int i = 0; i < n; i++) {
            if (i) cout << ' ';
            cout << perm[i];
        }
        cout << "\n";
    }
    return 0;
}