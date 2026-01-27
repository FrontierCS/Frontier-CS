#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(NULL);
    int N, M;
    cin >> N >> M;
    vector<bitset<1001>> adj(N);
    for (int i = 0; i < M; i++) {
        int u, v;
        cin >> u >> v;
        u--; v--;
        if (u != v && u >= 0 && v >= 0 && u < N && v < N) {
            adj[u][v] = 1;
            adj[v][u] = 1;
        }
    }
    bitset<1001> current;
    current.reset();
    for (int i = 0; i < N; i++) current.set(i);
    vector<int> clique;
    while (current.any()) {
        int best = -1;
        size_t maxd = (size_t)-1;
        for (int u = 0; u < N; u++) {
            if (current[u]) {
                size_t d = (adj[u] & current).count();
                if (d > maxd) {
                    maxd = d;
                    best = u;
                }
            }
        }
        if (best == -1) break;
        clique.push_back(best);
        current &= adj[best];
    }
    vector<int> selected(N, 0);
    for (int v : clique) selected[v] = 1;
    for (int i = 0; i < N; i++) {
        cout << selected[i] << '\n';
    }
    return 0;
}