#include <bits/stdc++.h>
using namespace std;

static const int MAXN = 1000;

int main() {
    setvbuf(stdout, nullptr, _IOFBF, 1 << 22);
    setvbuf(stdin,  nullptr, _IOFBF, 1 << 22);

    int n, m, T;
    if (scanf("%d %d %d", &n, &m, &T) != 3) return 0;

    vector<vector<int>> adj(n + 1);
    vector<int> indeg(n + 1, 0);
    vector<bitset<MAXN>> exist(n + 1);

    for (int i = 0; i < m; i++) {
        int a, b;
        scanf("%d %d", &a, &b);
        adj[a].push_back(b);
        indeg[b]++;
        if (b >= 1 && b <= MAXN) exist[a].set(b - 1);
    }

    // Topological order of initial DAG
    queue<int> q;
    for (int i = 1; i <= n; i++) if (indeg[i] == 0) q.push(i);

    vector<int> topo;
    topo.reserve(n);
    while (!q.empty()) {
        int u = q.front(); q.pop();
        topo.push_back(u);
        for (int v : adj[u]) {
            if (--indeg[v] == 0) q.push(v);
        }
    }
    // Fallback (shouldn't happen)
    if ((int)topo.size() != n) {
        vector<char> seen(n + 1, 0);
        for (int v : topo) seen[v] = 1;
        for (int i = 1; i <= n; i++) if (!seen[i]) topo.push_back(i);
    }

    vector<pair<int,int>> addEdges;
    addEdges.reserve(n * (n - 1) / 2 - m);

    // Add missing edges to make it a complete DAG along topo order
    for (int i = 0; i < n; i++) {
        int u = topo[i];
        for (int j = i + 1; j < n; j++) {
            int v = topo[j];
            if (!exist[u].test(v - 1)) {
                exist[u].set(v - 1);
                addEdges.emplace_back(u, v);
            }
        }
    }

    printf("%d\n", (int)addEdges.size());
    for (auto &e : addEdges) {
        printf("+ %d %d\n", e.first, e.second);
    }
    fflush(stdout);

    char resp[16];
    for (int tc = 0; tc < T; tc++) {
        // Query vertices 1..n-1. If all Win, answer is n.
        for (int i = 1; i <= n - 1; i++) {
            printf("? 1 %d\n", i);
        }
        fflush(stdout);

        int found = n;
        for (int i = 1; i <= n - 1; i++) {
            if (scanf("%15s", resp) != 1) return 0;
            if (strcmp(resp, "Lose") == 0) found = i;
        }

        printf("! %d\n", found);
        fflush(stdout);

        if (scanf("%15s", resp) != 1) return 0;
        if (strcmp(resp, "Wrong") == 0) return 0;
    }

    return 0;
}