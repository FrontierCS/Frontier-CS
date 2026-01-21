#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;

    string ans(N, '0');

    for (int i = 0; i < N; i++) {
        int m = i + 3;
        int sink0 = i + 1, sink1 = i + 2;

        vector<int> a(m), b(m);
        for (int x = 0; x < m; x++) a[x] = b[x] = x;

        for (int x = 0; x < i; x++) a[x] = b[x] = x + 1;

        a[i] = sink0;
        b[i] = sink1;

        a[sink0] = b[sink0] = sink0;
        a[sink1] = b[sink1] = sink1;

        cout << "1 " << m;
        for (int x = 0; x < m; x++) cout << ' ' << a[x];
        for (int x = 0; x < m; x++) cout << ' ' << b[x];
        cout << '\n';
        cout.flush();

        int x;
        if (!(cin >> x)) return 0;
        if (x == sink0) ans[i] = '0';
        else if (x == sink1) ans[i] = '1';
        else return 0;
    }

    cout << "0 " << ans << '\n';
    cout.flush();
    return 0;
}