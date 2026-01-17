#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    scanf("%d", &n);
    if (n == 1) {
        printf("!\n");
        fflush(stdout);
        return 0;
    }
    vector<vector<int>> on_path(n + 1, vector<int>(n + 1, 0));
    for (int v = 2; v <= n; ++v) {
        for (int u = 2; u <= n; ++u) {
            if (u == v) continue;
            printf("? 2 %d 1 %d\n", u, v);
            fflush(stdout);
            int res;
            scanf("%d", &res);
            if (res == -1) return 0;
            on_path[u][v] = res;
        }
    }
    vector<int> sizeA(n + 1, 0);
    sizeA[1] = 1;
    for (int v = 2; v <= n; ++v) {
        int cnt = 0;
        for (int u = 2; u <= n; ++u) {
            if (u != v && on_path[u][v]) ++cnt;
        }
        sizeA[v] = cnt + 2;
    }
    vector<pair<int, int>> edges;
    for (int v = 2; v <= n; ++v) {
        int target = sizeA[v] - 1;
        int par = -1;
        for (int u = 1; u <= n; ++u) {
            if (u == v) continue;
            bool is_anc = (u == 1) || (u >= 2 && u <= n && on_path[u][v]);
            if (is_anc && sizeA[u] == target) {
                par = u;
                break;
            }
        }
        assert(par != -1);
        edges.emplace_back(v, par);
    }
    printf("!\n");
    for (auto& e : edges) {
        printf("%d %d\n", e.first, e.second);
    }
    fflush(stdout);
    return 0;
}