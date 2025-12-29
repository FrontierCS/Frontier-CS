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
        unsigned long long K = ks[qi];
        vector<char> ops;
        unsigned long long x = K;
        while (x > 1) {
            if (x % 2 == 0) {
                ops.push_back('D'); // double
                x /= 2;
            } else {
                ops.push_back('A'); // add 1
                x -= 1;
            }
        }
        reverse(ops.begin(), ops.end());

        vector<int> perm;
        perm.reserve(ops.size());
        for (char op : ops) {
            int newval = (int)perm.size();
            if (op == 'D') {
                perm.push_back(newval);          // append new maximum
            } else { // 'A'
                perm.insert(perm.begin(), newval); // prepend new maximum
            }
        }

        int n = (int)perm.size();
        cout << n << "\n";
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << perm[i];
        }
        cout << "\n";
    }

    return 0;
}