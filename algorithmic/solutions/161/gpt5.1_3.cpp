#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M, K;
    if (!(cin >> N >> M >> K)) return 0;

    vector<long long> x(N), y(N);
    for (int i = 0; i < N; ++i) {
        cin >> x[i] >> y[i];
    }

    vector<int> u(M), v(M);
    vector<long long> w(M);
    for (int j = 0; j < M; ++j) {
        cin >> u[j] >> v[j] >> w[j];
        --u[j];
        --v[j];
    }

    vector<long long> ax(K), by(K);
    for (int k = 0; k < K; ++k) {
        cin >> ax[k] >> by[k];
    }

    vector<long long> maxd2(N, 0);

    for (int k = 0; k < K; ++k) {
        long long bestd2 = (long long)4e18;
        int best = -1;
        for (int i = 0; i < N; ++i) {
            long long dx = x[i] - ax[k];
            long long dy = y[i] - by[k];
            long long d2 = dx * dx + dy * dy;
            if (d2 < bestd2) {
                bestd2 = d2;
                best = i;
            }
        }
        if (best >= 0 && bestd2 > maxd2[best]) {
            maxd2[best] = bestd2;
        }
    }

    vector<int> P(N, 0);
    for (int i = 0; i < N; ++i) {
        long long v2 = maxd2[i];
        if (v2 == 0) {
            P[i] = 0;
        } else {
            long long r = (long long) sqrt((long double)v2);
            while (r * r < v2) ++r;
            if (r > 5000) r = 5000;
            P[i] = (int)r;
        }
    }

    vector<int> B(M, 1);

    for (int i = 0; i < N; ++i) {
        if (i) cout << ' ';
        cout << P[i];
    }
    cout << '\n';
    for (int j = 0; j < M; ++j) {
        if (j) cout << ' ';
        cout << B[j];
    }
    cout << '\n';

    return 0;
}