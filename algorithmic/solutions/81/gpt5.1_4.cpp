#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;

    string S(N, '0');

    for (int j = 0; j < N; ++j) {
        int m = j + 3; // ensures 1 <= m <= 1002 for N = 1000
        vector<int> a(m), b(m);
        for (int i = 0; i < m; ++i) {
            a[i] = i;
            b[i] = i;
        }
        for (int k = 0; k < j; ++k) {
            a[k] = k + 1;
            b[k] = k + 1;
        }
        int A = j + 1;
        int B = j + 2;
        a[j] = A;
        b[j] = B;

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

        if (x == A) S[j] = '0';
        else if (x == B) S[j] = '1';
        else S[j] = '0'; // fallback, should not happen in a valid interaction
    }

    cout << 0 << "\n";
    cout << S << "\n";
    cout.flush();

    return 0;
}