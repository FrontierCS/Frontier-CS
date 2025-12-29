#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M, K;
    if (!(cin >> N >> M >> K)) return 0;

    vector<long long> x(N), y(N);
    for (int i = 0; i < N; ++i) cin >> x[i] >> y[i];

    vector<int> u(M), v(M);
    vector<long long> w(M);
    for (int j = 0; j < M; ++j) cin >> u[j] >> v[j] >> w[j];

    vector<long long> a(K), b(K);
    for (int k = 0; k < K; ++k) cin >> a[k] >> b[k];

    // All P_i = 0
    for (int i = 0; i < N; ++i) {
        if (i) cout << ' ';
        cout << 0;
    }
    cout << '\n';

    // All B_j = 0 (all edges OFF)
    for (int j = 0; j < M; ++j) {
        if (j) cout << ' ';
        cout << 0;
    }
    cout << '\n';

    return 0;
}