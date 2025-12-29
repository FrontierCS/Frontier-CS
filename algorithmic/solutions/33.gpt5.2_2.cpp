#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int q;
    cin >> q;
    for (int _ = 0; _ < q; _++) {
        unsigned long long k;
        cin >> k;

        vector<char> ops_rev;
        while (k > 1) {
            if ((k & 1ULL) == 0) {
                ops_rev.push_back('M'); // last operation was "append new maximum" => *2
                k >>= 1;
            } else {
                ops_rev.push_back('m'); // last operation was "append new minimum" => +1
                k -= 1;
            }
        }
        reverse(ops_rev.begin(), ops_rev.end());

        int n = (int)ops_rev.size();
        int L = 0;
        for (char c : ops_rev) if (c == 'm') L++;
        int M = n - L;

        vector<int> p;
        p.reserve(n);

        long long maxVal = L;     // values for max-ops: L, L+1, ..., n-1
        long long minVal = L - 1; // values for min-ops: L-1, L-2, ..., 0

        for (char c : ops_rev) {
            if (c == 'M') p.push_back((int)maxVal++);
            else p.push_back((int)minVal--);
        }

        cout << n << "\n";
        for (int i = 0; i < n; i++) {
            if (i) cout << ' ';
            cout << p[i];
        }
        cout << "\n";
    }
    return 0;
}