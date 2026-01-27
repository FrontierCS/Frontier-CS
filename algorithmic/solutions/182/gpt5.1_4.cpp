#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;

    vector<vector<int>> adj(N + 1);
    vector<char> inCover(N + 1, 0);

    // Greedy maximal matching while reading edges
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        adj[u].push_back(v);
        adj[v].push_back(u);
        if (!inCover[u] && !inCover[v]) {
            inCover[u] = inCover[v] = 1;
        }
    }

    // Randomized order for removal heuristic
    vector<int> order(N);
    for (int i = 0; i < N; ++i) order[i] = i + 1;

    mt19937_64 rng((uint64_t)chrono::steady_clock::now().time_since_epoch().count());
    shuffle(order.begin(), order.end(), rng);

    // Try to remove vertices while preserving vertex cover property
    for (int u : order) {
        if (!inCover[u]) continue;
        bool canRemove = true;
        for (int v : adj[u]) {
            if (!inCover[v]) {
                canRemove = false;
                break;
            }
        }
        if (canRemove) inCover[u] = 0;
    }

    // Output result
    for (int i = 1; i <= N; ++i) {
        cout << (inCover[i] ? 1 : 0) << '\n';
    }

    return 0;
}