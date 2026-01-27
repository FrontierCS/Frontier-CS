#include <bits/stdc++.h>
using namespace std;

static inline void flush() {
    cout.flush();
}

long long ask_pair(int i, int j) {
    cout << "? 1 1\n";
    cout << i << "\n";
    cout << j << "\n";
    flush();
    long long F;
    if (!(cin >> F)) exit(0);
    return F;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        cin >> n;

        int ref1 = -1, ref2 = -1;
        bool found = false;

        // Find any pair of non-zero magnets using safe (1,1) queries
        for (int i = 1; i <= n && !found; ++i) {
            for (int j = i + 1; j <= n; ++j) {
                long long f = ask_pair(i, j);
                if (f != 0) {
                    ref1 = i;
                    ref2 = j;
                    found = true;
                    break;
                }
            }
        }

        // Classify zeros using ref1 as non-zero
        vector<int> zeros;
        if (found) {
            for (int k = 1; k <= n; ++k) {
                if (k == ref1 || k == ref2) continue;
                long long f = ask_pair(ref1, k);
                if (f == 0) zeros.push_back(k);
            }
        } else {
            // Should not happen due to guarantees, but handle gracefully: assume all except two are zeros unknown
            // We cannot determine which two are non-zero without a non-zero pair found; default to empty zeros
        }

        cout << "! " << zeros.size();
        for (int z : zeros) cout << " " << z;
        cout << "\n";
        flush();
    }
    return 0;
}