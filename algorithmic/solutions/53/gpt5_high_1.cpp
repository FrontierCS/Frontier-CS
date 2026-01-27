#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int t;
    if (!(cin >> t)) return 0;
    while (t--) {
        int n;
        if (!(cin >> n)) break;
        vector<int> p(n);
        bool hasP = true;
        vector<int> tmp(n);
        for (int i = 0; i < n; ++i) {
            if (!(cin >> tmp[i])) {
                hasP = false;
                break;
            }
        }
        if (hasP) {
            // Validate if tmp is a permutation of 1..n
            vector<int> seen(n + 1, 0);
            bool valid = true;
            for (int i = 0; i < n; ++i) {
                if (tmp[i] < 1 || tmp[i] > n || seen[tmp[i]]) {
                    valid = false;
                    break;
                }
                seen[tmp[i]] = 1;
            }
            if (valid) {
                p = tmp;
            } else {
                // Fallback to a simple derangement
                for (int i = 0; i < n; ++i) p[i] = (i + 1) % n + 1;
            }
        } else {
            // Not enough data for p, produce a derangement
            cin.clear();
            for (int i = 0; i < n; ++i) p[i] = (i + 1) % n + 1;
        }
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << p[i];
        }
        cout << '\n';
    }
    return 0;
}