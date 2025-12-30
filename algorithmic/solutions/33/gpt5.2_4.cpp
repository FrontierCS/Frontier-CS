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

        int highest = 63 - __builtin_clzll(k); // highest set bit index (k >= 1)
        vector<long long> ranks;
        long long low = 0, high = -1;

        auto add_max = [&]() {
            if (ranks.empty()) {
                ranks.push_back(0);
                low = high = 0;
            } else {
                ++high;
                ranks.push_back(high);
            }
        };
        auto add_min = [&]() {
            if (ranks.empty()) {
                ranks.push_back(0);
                low = high = 0;
            } else {
                --low;
                ranks.push_back(low);
            }
        };

        for (int i = highest - 1; i >= 0; --i) {
            add_max(); // T *= 2
            if ((k >> i) & 1ULL) add_min(); // T += 1
        }

        long long offset = -low;
        int n = (int)ranks.size();
        cout << n << "\n";
        for (int i = 0; i < n; ++i) {
            long long v = ranks[i] + offset;
            if (i) cout << ' ';
            cout << v;
        }
        cout << "\n";
    }
    return 0;
}