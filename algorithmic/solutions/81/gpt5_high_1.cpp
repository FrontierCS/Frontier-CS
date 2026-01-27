#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;

    string S(N, '0');

    for (int i = 0; i < N; ++i) {
        int m = i + 3; // states: 0..i (chain), i+1 (sink for 0), i+2 (sink for 1)
        vector<int> a(m), b(m);
        // Build chain for steps 0..i-1
        for (int j = 0; j < i; ++j) {
            a[j] = j + 1;
            b[j] = j + 1;
        }
        // Branch at step i
        a[i] = i + 1;     // sink for '0'
        b[i] = i + 2;     // sink for '1'
        // Sinks
        a[i + 1] = i + 1; b[i + 1] = i + 1;
        a[i + 2] = i + 2; b[i + 2] = i + 2;

        cout << 1 << '\n';
        cout << m << '\n';
        for (int j = 0; j < m; ++j) {
            if (j) cout << ' ';
            cout << a[j];
        }
        cout << '\n';
        for (int j = 0; j < m; ++j) {
            if (j) cout << ' ';
            cout << b[j];
        }
        cout << '\n';
        cout.flush();

        int x;
        if (!(cin >> x)) return 0;
        if (x < 0) return 0;

        S[i] = (x == i + 2) ? '1' : '0';
    }

    cout << 0 << '\n';
    cout << S << '\n';
    cout.flush();
    return 0;
}