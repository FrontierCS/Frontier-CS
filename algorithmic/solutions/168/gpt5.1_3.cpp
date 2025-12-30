#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M, H;
    if (!(cin >> N >> M >> H)) return 0;

    vector<int> A(N);
    for (int i = 0; i < N; ++i) cin >> A[i];

    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
    }

    for (int i = 0; i < N; ++i) {
        int x, y;
        cin >> x >> y;
    }

    for (int i = 0; i < N; ++i) {
        if (i) cout << ' ';
        cout << -1;
    }
    cout << '\n';

    return 0;
}