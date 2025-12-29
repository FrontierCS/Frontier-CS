#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    long long first, second;
    if (!(cin >> first >> second)) return 0;

    int N, M;
    vector<int> x, y;
    vector<int> u, v;

    if (second > 800) {
        // Format: N M, then coordinates
        N = (int)first;
        M = (int)second;
        x.assign(N, 0);
        y.assign(N, 0);
        for (int i = 0; i < N; i++) cin >> x[i] >> y[i];
    } else {
        // Format: coordinates only, N=400, M=5*(N-1)
        N = 400;
        M = 5 * (N - 1);
        x.assign(N, 0);
        y.assign(N, 0);
        x[0] = (int)first;
        y[0] = (int)second;
        for (int i = 1; i < N; i++) cin >> x[i] >> y[i];
    }

    u.assign(M, 0);
    v.assign(M, 0);
    for (int i = 0; i < M; i++) cin >> u[i] >> v[i];

    for (int i = 0; i < M; i++) {
        long long l;
        if (!(cin >> l)) return 0;
        cout << 1 << '\n';
        cout.flush();
    }

    return 0;
}