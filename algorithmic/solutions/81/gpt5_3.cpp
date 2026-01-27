#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N;
    if (!(cin >> N)) return 0;

    string ans(N, '0');

    for (int i = 0; i < N; ++i) {
        int m = i + 3;
        int p = i + 1;
        int q = i + 2;
        vector<int> a(m), b(m);
        for (int x = 0; x < m; ++x) {
            a[x] = x;
            b[x] = x;
        }
        for (int x = 0; x < i; ++x) {
            a[x] = x + 1;
            b[x] = x + 1;
        }
        a[i] = p;
        b[i] = q;

        cout << 1 << '\n';
        cout << m << '\n';
        for (int x = 0; x < m; ++x) {
            if (x) cout << ' ';
            cout << a[x];
        }
        cout << '\n';
        for (int x = 0; x < m; ++x) {
            if (x) cout << ' ';
            cout << b[x];
        }
        cout << '\n';
        cout.flush();

        int res;
        if (!(cin >> res)) return 0;
        if (res < 0) return 0;

        if (res == p) ans[i] = '0';
        else if (res == q) ans[i] = '1';
        else ans[i] = '0'; // Fallback (should not happen with correct interactor)
    }

    cout << 0 << '\n';
    cout << ans << '\n';
    cout.flush();

    return 0;
}