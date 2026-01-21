#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;

    string ans;
    ans.reserve(N);

    const int M = N + 2; // 1002 for N=1000

    for (int k = 0; k < N; ++k) {
        int m = M;
        vector<int> a(m), b(m);

        // Initialize as self-loops
        for (int i = 0; i < m; ++i) {
            a[i] = i;
            b[i] = i;
        }

        int s0 = k + 1;
        int s1 = k + 2;

        // Prefix chain: 0 -> 1 -> ... -> k
        for (int j = 0; j < k; ++j) {
            a[j] = j + 1;
            b[j] = j + 1;
        }

        // Branch at position k
        a[k] = s0;
        b[k] = s1;

        // s0 and s1 already self-loop from initialization

        // Output query
        cout << 1 << '\n';
        cout << m << '\n';
        for (int i = 0; i < m; ++i) {
            if (i) cout << ' ';
            cout << a[i];
        }
        cout << '\n';
        for (int i = 0; i < m; ++i) {
            if (i) cout << ' ';
            cout << b[i];
        }
        cout << '\n';
        cout.flush();

        int x;
        if (!(cin >> x)) return 0;
        if (x == s0) ans.push_back('0');
        else ans.push_back('1');
    }

    // Output guess
    cout << 0 << '\n';
    cout << ans << '\n';
    cout.flush();

    return 0;
}