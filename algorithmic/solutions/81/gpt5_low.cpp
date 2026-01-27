#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;

    string S(N, '0');

    for (int i = 0; i < N; ++i) {
        int m = i + 3; // states: 0..i (chain), i+1 (sink0), i+2 (sink1)
        vector<int> a(m), b(m);
        // chain for steps before i
        for (int x = 0; x <= i - 1; ++x) {
            a[x] = x + 1;
            b[x] = x + 1;
        }
        // branching at step i
        a[i] = i + 1;     // sink0
        b[i] = i + 2;     // sink1
        // sinks self-loop
        a[i + 1] = i + 1; b[i + 1] = i + 1;
        a[i + 2] = i + 2; b[i + 2] = i + 2;

        cout << 1 << "\n";
        cout << m << "\n";
        for (int x = 0; x < m; ++x) {
            if (x) cout << ' ';
            cout << a[x];
        }
        cout << "\n";
        for (int x = 0; x < m; ++x) {
            if (x) cout << ' ';
            cout << b[x];
        }
        cout << "\n";
        cout.flush();

        int x;
        if (!(cin >> x)) return 0;
        if (x == i + 1) S[i] = '0';
        else if (x == i + 2) S[i] = '1';
        else {
            // Fallback in case of unexpected response
            S[i] = '0';
        }
    }

    cout << 0 << "\n";
    cout << S << "\n";
    cout.flush();

    return 0;
}