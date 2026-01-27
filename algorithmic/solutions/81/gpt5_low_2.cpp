#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;

    int m = N + 1;
    string S(N, '0');

    for (int k = 0; k < N; ++k) {
        vector<int> a(m), b(m);
        // Default self-loops
        for (int i = 0; i < m; ++i) {
            a[i] = i;
            b[i] = i;
        }
        // Counter chain up to k
        for (int i = 0; i < k; ++i) {
            a[i] = i + 1;
            b[i] = i + 1;
        }
        // Branch at position k
        if (k < N) {
            a[k] = N;     // if S_k == '0' -> state N
            b[k] = N - 1; // if S_k == '1' -> state N-1
        }

        cout << 1 << "\n";
        cout << m << "\n";
        for (int i = 0; i < m; ++i) {
            if (i) cout << ' ';
            cout << a[i];
        }
        cout << "\n";
        for (int i = 0; i < m; ++i) {
            if (i) cout << ' ';
            cout << b[i];
        }
        cout << "\n";
        cout.flush();

        int x;
        if (!(cin >> x)) return 0;
        if (x == N) S[k] = '0';
        else S[k] = '1';
    }

    cout << 0 << "\n";
    cout << S << "\n";
    cout.flush();
    return 0;
}