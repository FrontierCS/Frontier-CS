#include <bits/stdc++.h>
using namespace std;

const int MAXN = 500;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, M;
    if (!(cin >> N >> M)) return 0;

    vector<vector<int>> adj(N);
    for (int i = 0; i < M; ++i) {
        int u, v;
        cin >> u >> v;
        if (u == v) continue;
        --u; --v;
        adj[u].push_back(v);
        adj[v].push_back(u);
    }

    vector<int> degree(N);
    for (int i = 0; i < N; ++i) degree[i] = (int)adj[i].size();

    vector<int> color(N, 0);
    vector<int> sat_deg(N, 0);
    vector< bitset<MAXN + 1> > neighborColors(N);
    vector<char> colored(N, 0);

    // Choose first vertex: maximum degree
    int first = 0;
    for (int i = 1; i < N; ++i)
        if (degree[i] > degree[first])
            first = i;

    int maxColorUsed = 1;
    color[first] = 1;
    colored[first] = 1;

    for (int u : adj[first]) {
        if (colored[u]) continue;
        if (!neighborColors[u].test(1)) {
            neighborColors[u].set(1);
            sat_deg[u]++;
        }
    }

    for (int step = 1; step < N; ++step) {
        int best = -1;
        for (int i = 0; i < N; ++i) {
            if (colored[i]) continue;
            if (best == -1 ||
                sat_deg[i] > sat_deg[best] ||
                (sat_deg[i] == sat_deg[best] && degree[i] > degree[best]) ||
                (sat_deg[i] == sat_deg[best] && degree[i] == degree[best] && i < best)) {
                best = i;
            }
        }

        int v = best;
        int chosen = 0;
        for (int c = 1; c <= maxColorUsed; ++c) {
            if (!neighborColors[v].test(c)) {
                chosen = c;
                break;
            }
        }
        if (chosen == 0) {
            chosen = ++maxColorUsed;
        }

        color[v] = chosen;
        colored[v] = 1;

        for (int u : adj[v]) {
            if (colored[u]) continue;
            if (!neighborColors[u].test(chosen)) {
                neighborColors[u].set(chosen);
                sat_deg[u]++;
            }
        }
    }

    for (int i = 0; i < N; ++i) {
        cout << color[i] << '\n';
    }

    return 0;
}