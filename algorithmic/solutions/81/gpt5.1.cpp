#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;

    string S;
    S.reserve(N);

    for (int i = 0; i < N; ++i) {
        int m = i + 3;
        vector<int> a(m, 0), b(m, 0);

        int cur = 0;
        for (int k = 0; k < i; ++k) {
            int nxt = k + 1;
            if (S[k] == '0') {
                a[cur] = nxt;
            } else {
                b[cur] = nxt;
            }
            cur = nxt;
        }

        int x0 = i + 1;
        int x1 = i + 2;

        a[cur] = x0;
        b[cur] = x1;

        a[x0] = x0;
        b[x0] = x0;
        a[x1] = x1;
        b[x1] = x1;

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

        int res;
        if (!(cin >> res)) return 0;
        if (res == x0) S.push_back('0');
        else S.push_back('1');
    }

    cout << 0 << '\n';
    cout << S << '\n';
    cout.flush();

    return 0;
}