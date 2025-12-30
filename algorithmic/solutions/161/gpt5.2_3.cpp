#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M, K;
    if (!(cin >> N >> M >> K)) return 0;

    vector<int> x(N+1), y(N+1);
    for (int i = 1; i <= N; i++) cin >> x[i] >> y[i];

    for (int j = 0; j < M; j++) {
        int u, v;
        long long w;
        cin >> u >> v >> w;
    }

    for (int k = 0; k < K; k++) {
        int a, b;
        cin >> a >> b;
    }

    // Simple always-feasible solution:
    // - Turn on all edges so all vertices are reachable from vertex 1.
    // - Set maximum power on all vertices to cover all residents (guaranteed within 5000 of some vertex).
    for (int i = 1; i <= N; i++) {
        if (i > 1) cout << ' ';
        cout << 5000;
    }
    cout << "\n";

    for (int j = 1; j <= M; j++) {
        if (j > 1) cout << ' ';
        cout << 1;
    }
    cout << "\n";

    return 0;
}