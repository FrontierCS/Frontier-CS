#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;

    string S(N, '0');
    int K = N;
    int m = K + 2;

    for (int i = 0; i < N; ++i) {
        vector<int> a(m), b(m);
        for (int x = 0; x < K; ++x) {
            a[x] = (x + 1) % K;
            b[x] = (x + 1) % K;
        }
        a[i] = K;
        b[i] = K + 1;
        a[K] = K; b[K] = K;
        a[K + 1] = K + 1; b[K + 1] = K + 1;

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

        int res;
        if (!(cin >> res)) return 0;
        if (res == -1) return 0;
        if (res == K + 1) S[i] = '1';
        else S[i] = '0';
    }

    cout << 0 << "\n";
    cout << S << "\n";
    cout.flush();

    return 0;
}