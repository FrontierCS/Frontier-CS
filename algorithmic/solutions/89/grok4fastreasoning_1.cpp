#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    scanf("%d", &n);
    bool onpath[1005][1005];
    memset(onpath, 0, sizeof(onpath));
    for (int i = 1; i <= n; i++) {
        onpath[i][i] = true;
    }
    int depth[1005];
    depth[1] = 0;
    for (int v = 2; v <= n; v++) {
        onpath[1][v] = true;
        for (int u = 2; u <= n; u++) {
            if (u == v) continue;
            printf("? 2 %d 1 %d\n", u, v);
            fflush(stdout);
            int res;
            scanf("%d", &res);
            if (res == -1) return 0;
            onpath[u][v] = (res == 1);
        }
    }
    for (int v = 2; v <= n; v++) {
        int cnt = 0;
        for (int u = 1; u <= n; u++) {
            if (onpath[u][v]) cnt++;
        }
        depth[v] = cnt - 1;
    }
    vector<pair<int, int>> edges;
    for (int v = 2; v <= n; v++) {
        int maxd = -1;
        int par = -1;
        for (int u = 1; u <= n; u++) {
            if (u != v && onpath[u][v] && depth[u] > maxd) {
                maxd = depth[u];
                par = u;
            }
        }
        edges.push_back({par, v});
    }
    printf("!\n");
    fflush(stdout);
    for (auto [a, b] : edges) {
        printf("%d %d\n", a, b);
    }
    fflush(stdout);
    return 0;
}