#include <bits/stdc++.h>
using namespace std;

static const int MAXN = 1005;

static inline int ask_on_path_1_to_v(int check, int v) {
    // Query: is 'check' on path between 1 and v?
    printf("? 2 %d 1 %d\n", check, v);
    fflush(stdout);
    int ans;
    if (scanf("%d", &ans) != 1) exit(0);
    if (ans == -1) exit(0);
    return ans;
}

int main() {
    int n;
    if (scanf("%d", &n) != 1) return 0;

    if (n == 1) {
        printf("!\n");
        fflush(stdout);
        return 0;
    }

    vector<bitset<MAXN>> anc(n + 1);
    vector<int> sz(n + 1, 0), parent(n + 1, 0);

    anc[1].set(1);

    for (int v = 2; v <= n; v++) {
        anc[v].set(1);
        anc[v].set(v);
        for (int u = 2; u <= n; u++) {
            if (u == v) continue;
            int ans = ask_on_path_1_to_v(u, v);
            if (ans == 1) anc[v].set(u);
        }
    }

    for (int v = 1; v <= n; v++) sz[v] = (int)anc[v].count();

    parent[1] = 0;
    for (int v = 2; v <= n; v++) {
        int best = 1;
        int bestSz = sz[1];
        for (int u = 2; u <= n; u++) {
            if (u == v) continue;
            if (anc[v].test(u) && sz[u] > bestSz) {
                best = u;
                bestSz = sz[u];
            }
        }
        parent[v] = best;
    }

    printf("!\n");
    for (int v = 2; v <= n; v++) {
        printf("%d %d\n", parent[v], v);
    }
    fflush(stdout);
    return 0;
}