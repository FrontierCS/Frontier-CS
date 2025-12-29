#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M, K;
    if (!(cin >> N >> M >> K)) return 0;

    vector<int> x(N), y(N);
    for (int i = 0; i < N; i++) {
        cin >> x[i] >> y[i];
    }

    vector<int> u(M), v(M);
    vector<long long> w(M);
    for (int j = 0; j < M; j++) {
        cin >> u[j] >> v[j] >> w[j];
        --u[j];
        --v[j];
    }

    vector<int> a(K), b(K);
    for (int k = 0; k < K; k++) {
        cin >> a[k] >> b[k];
    }

    // For each vertex, store max distance to assigned residents
    vector<double> maxDist(N, 0.0);

    for (int k = 0; k < K; k++) {
        long long bestDist2 = (1LL << 62);
        int bestIdx = -1;
        for (int i = 0; i < N; i++) {
            long long dx = (long long)x[i] - a[k];
            long long dy = (long long)y[i] - b[k];
            long long dist2 = dx * dx + dy * dy;
            if (dist2 < bestDist2) {
                bestDist2 = dist2;
                bestIdx = i;
            }
        }
        if (bestIdx != -1) {
            double dist = sqrt((double)bestDist2);
            if (dist > 5000.0) dist = 5000.0;
            if (dist > maxDist[bestIdx]) maxDist[bestIdx] = dist;
        }
    }

    vector<int> P(N, 0);
    for (int i = 0; i < N; i++) {
        int pi = (int)ceil(maxDist[i]);
        if (pi < 0) pi = 0;
        if (pi > 5000) pi = 5000;
        P[i] = pi;
    }

    // Output P_1 ... P_N
    for (int i = 0; i < N; i++) {
        if (i) cout << ' ';
        cout << P[i];
    }
    cout << '\n';

    // Turn all edges ON
    for (int j = 0; j < M; j++) {
        if (j) cout << ' ';
        cout << 1;
    }
    cout << '\n';

    return 0;
}