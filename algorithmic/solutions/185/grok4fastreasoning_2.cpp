#include <bits/stdc++.h>
using namespace std;

const int MAXN = 1005;
bitset<MAXN> adj[MAXN];

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int N, M;
    cin >> N >> M;
    for (int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        adj[u][v] = 1;
        adj[v][u] = 1;
    }
    bitset<MAXN> R;
    for (int i = 1; i <= N; i++) R.set(i);
    vector<int> selected(N + 1, 0);
    while (R.any()) {
        int best_v = -1;
        int max_deg = -1;
        for (int i = 1; i <= N; i++) {
            if (!R[i]) continue;
            int deg = (adj[i] & R).count();
            if (deg > max_deg || (deg == max_deg && i < best_v)) {
                max_deg = deg;
                best_v = i;
            }
        }
        selected[best_v] = 1;
        R &= adj[best_v];
    }
    for (int i = 1; i <= N; i++) {
        cout << selected[i] << '\n';
    }
    return 0;
}