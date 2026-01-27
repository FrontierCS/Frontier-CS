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
        unsigned long long k = ks[qi];
        vector<char> ops;

        int h = 63 - __builtin_clzll(k);
        for (int i = h - 1; i >= 0; --i) {
            ops.push_back('M'); // new max -> double
            if ((k >> i) & 1ULL) ops.push_back('m'); // new min -> +1
        }

        int n = (int)ops.size();
        cout << n << "\n";
        long long curMin = 0, curMax = -1;
        vector<long long> arr;
        arr.reserve(n);
        for (char c : ops) {
            if (c == 'M') {
                ++curMax;
                arr.push_back(curMax);
            } else {
                --curMin;
                arr.push_back(curMin);
            }
        }
        long long shift = -curMin;
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << (arr[i] + shift);
        }
        cout << "\n";
    }
    return 0;
}