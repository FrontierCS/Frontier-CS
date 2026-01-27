#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;
    string S(N, '0');

    const int K = 1000; // number of position states
    const int m = K + 2; // include two sink states
    const int C0 = K, C1 = K + 1;

    for (int t = 0; t < N; ++t) {
        vector<int> a(m), b(m);

        // Initialize P states to advance position modulo K
        for (int j = 0; j < K; ++j) {
            int nxt = (j + 1) % K;
            a[j] = nxt;
            b[j] = nxt;
        }
        // Branch at position t
        a[t] = C0;
        b[t] = C1;

        // Sink states: self-loop
        a[C0] = C0; b[C0] = C0;
        a[C1] = C1; b[C1] = C1;

        cout << 1 << ' ' << m << '\n';
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
        if (x == C0) S[t] = '0';
        else if (x == C1) S[t] = '1';
        else {
            // Should not happen; default to '0'
            S[t] = '0';
        }
    }

    cout << 0 << ' ' << S << '\n';
    cout.flush();
    return 0;
}