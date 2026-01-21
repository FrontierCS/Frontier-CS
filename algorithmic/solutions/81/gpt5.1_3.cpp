#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;

    string ans(N, '0');

    for (int k = 0; k < N; ++k) {
        int m = k + 3;
        vector<int> a(m), b(m);

        // States 0..k-1: move to i+1 regardless of bit
        for (int i = 0; i < k; ++i) {
            a[i] = i + 1;
            b[i] = i + 1;
        }

        int A = k + 1;
        int B = k + 2;

        // State k: capture S_k
        a[k] = A; // if S_k == '0'
        b[k] = B; // if S_k == '1'

        // States A and B: self-loops
        a[A] = A;
        b[A] = A;
        a[B] = B;
        b[B] = B;

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
        if (x == -1) return 0; // in case of judge error signal

        if (x == A) ans[k] = '0';
        else if (x == B) ans[k] = '1';
        else return 0; // unexpected, but safer
    }

    // Output final guess
    cout << 0 << '\n';
    cout << ans << '\n';
    cout.flush();

    return 0;
}