#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;

    int m = N + 2;
    vector<int> a(m), b(m);
    string ans(N, '0');

    for (int k = 0; k < N; ++k) {
        for (int i = 0; i < m; ++i) {
            a[i] = i;
            b[i] = i;
        }
        for (int i = 0; i < k; ++i) {
            a[i] = i + 1;
            b[i] = i + 1;
        }
        a[k] = N;
        b[k] = N + 1;
        a[N] = N; b[N] = N;
        a[N + 1] = N + 1; b[N + 1] = N + 1;

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
        if (x < 0) return 0;
        if (x == N) ans[k] = '0';
        else if (x == N + 1) ans[k] = '1';
        else ans[k] = '0';
    }

    cout << 0 << '\n';
    cout << ans << '\n';
    cout.flush();

    return 0;
}