#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    const long long MOD = 1000000007LL;
    int n;
    if (!(cin >> n)) return 0;

    vector<int> ops(n + 1, 0); // 0 -> '+', 1 -> '*'
    long long cntPlusSuffix = 0;

    for (int i = n; i >= 1; --i) {
        vector<long long> a(n + 1, 1);
        for (int k = 0; k < i; ++k) a[k] = 0; // a0..a_{i-1} = 0
        a[i] = 1; // ai = 1
        for (int k = i + 1; k <= n; ++k) a[k] = 1; // suffix = 1

        cout << "?";
        for (int k = 0; k <= n; ++k) {
            cout << " " << a[k];
        }
        cout << "\n" << flush;

        long long r;
        if (!(cin >> r)) return 0;
        if (r == -1) return 0;

        long long Ci = cntPlusSuffix % MOD;
        if (r == (Ci + 1) % MOD) {
            ops[i] = 0; // '+'
            cntPlusSuffix++;
        } else {
            ops[i] = 1; // '*'
        }
    }

    cout << "!";
    for (int i = 1; i <= n; ++i) {
        cout << " " << ops[i];
    }
    cout << "\n" << flush;

    return 0;
}