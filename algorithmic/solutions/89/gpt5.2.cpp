#include <bits/stdc++.h>
using namespace std;

static int n;

static int query_on_path_root(int u, int v) {
    // ask if vertex u lies on path(1, v)
    printf("? 2 %d 1 %d\n", u, v);
    fflush(stdout);
    int ans;
    if (scanf("%d", &ans) != 1) exit(0);
    if (ans == -1) exit(0);
    return ans;
}

int main() {
    if (scanf("%d", &n) != 1) return 0;

    vector<vector<unsigned char>> anc(n + 1, vector<unsigned char>(n + 1, 0));

    // Fill known reflexive/obvious values
    for (int v = 1; v <= n; v++) {
        anc[1][v] = 1;
        anc[v][v] = 1;
    }
    for (int u = 2; u <= n; u++) anc[u][1] = 0;

    // Query anc[u][v] = 1 iff u is on path(1, v)
    for (int v = 2; v <= n; v++) {
        for (int u = 2; u <= n; u++) {
            if (u == v) continue;
            anc[u][v] = (unsigned char)query_on_path_root(u, v);
        }
    }

    vector<int> parent(n + 1, 0);
    parent[1] = 0;

    for (int b = 2; b <= n; b++) {
        int p = 1;
        for (int a = 2; a <= n; a++) {
            if (a == b) continue;
            if (!anc[a][b]) continue;         // a not an ancestor of b
            if (p != a && anc[p][a]) p = a;   // a is deeper than current p
        }
        parent[b] = p;
    }

    printf("!\n");
    for (int b = 2; b <= n; b++) {
        printf("%d %d\n", parent[b], b);
    }
    fflush(stdout);
    return 0;
}