#include <bits/stdc++.h>
using namespace std;

static inline void die() {
    fflush(stdout);
    exit(0);
}

int main() {
    int n;
    if (scanf("%d", &n) != 1) return 0;

    auto ask_on_path = [&](int x, int a, int b) -> int {
        // Query whether vertex x lies on the path between a and b (Steiner({a,b}))
        printf("? 2 %d %d %d\n", x, a, b);
        fflush(stdout);
        int ans;
        if (scanf("%d", &ans) != 1) die();
        if (ans == -1) die();
        return ans;
    };

    if (n <= 1) {
        printf("!\n");
        fflush(stdout);
        return 0;
    }

    int W = (n + 63) / 64;
    vector<vector<uint64_t>> anc(n + 1, vector<uint64_t>(W, 0));
    vector<int> sz(n + 1, 0), parent(n + 1, 0);

    auto setBit = [&](vector<uint64_t>& bs, int idx) {
        --idx;
        bs[idx >> 6] |= (1ULL << (idx & 63));
    };
    auto getBit = [&](const vector<uint64_t>& bs, int idx) -> bool {
        --idx;
        return (bs[idx >> 6] >> (idx & 63)) & 1ULL;
    };

    // Root the tree at 1. Compute Anc[v] = vertices on path(1, v) (inclusive).
    setBit(anc[1], 1);
    sz[1] = 1;

    for (int v = 2; v <= n; v++) {
        setBit(anc[v], 1);
        setBit(anc[v], v);
        sz[v] = 2;
        for (int u = 2; u <= n; u++) {
            if (u == v) continue;
            int res = ask_on_path(u, 1, v);
            if (res == 1) {
                setBit(anc[v], u);
                sz[v]++;
            }
        }
    }

    // Parent is the deepest proper ancestor: among u in Anc[v]\{v}, maximize |Anc[u]|.
    for (int v = 2; v <= n; v++) {
        int best = 1;
        int bestSz = sz[1];
        for (int u = 1; u <= n; u++) {
            if (u == v) continue;
            if (getBit(anc[v], u)) {
                if (sz[u] > bestSz) {
                    bestSz = sz[u];
                    best = u;
                }
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