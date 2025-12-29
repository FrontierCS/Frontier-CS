#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int q;
    if (!(cin >> q)) return 0;
    vector<long long> ks(q);
    for (int i = 0; i < q; ++i) cin >> ks[i];

    for (int qi = 0; qi < q; ++qi) {
        long long k = ks[qi];
        long long T = k - 1; // number of non-empty increasing subsequences

        vector<char> ops_rev;
        while (T > 0) {
            if (T % 2 == 0) {
                ops_rev.push_back('S'); // append smallest
                T -= 1;
            } else {
                ops_rev.push_back('L'); // append largest
                T = (T - 1) / 2;
            }
        }
        reverse(ops_rev.begin(), ops_rev.end());

        int n = (int)ops_rev.size();
        vector<long long> val(n);
        long long minv = 0, maxv = -1;

        for (int i = 0; i < n; ++i) {
            char op = ops_rev[i];
            if (op == 'L') {
                ++maxv;
                val[i] = maxv;
            } else { // 'S'
                --minv;
                val[i] = minv;
            }
        }

        long long shift = -minv;
        cout << n << '\n';
        for (int i = 0; i < n; ++i) {
            if (i) cout << ' ';
            cout << val[i] + shift;
        }
        cout << '\n';
    }

    return 0;
}