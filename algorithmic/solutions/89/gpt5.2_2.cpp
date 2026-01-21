#include <bits/stdc++.h>
using namespace std;

static inline int fastReadInt() {
    int c = getchar();
    while (c != '-' && (c < '0' || c > '9')) c = getchar();
    int sgn = 1;
    if (c == '-') { sgn = -1; c = getchar(); }
    int x = 0;
    while (c >= '0' && c <= '9') { x = x * 10 + (c - '0'); c = getchar(); }
    return x * sgn;
}

static inline int askPath(int x, int a, int b) {
    printf("? 2 %d %d %d\n", x, a, b);
    fflush(stdout);
    int res = fastReadInt();
    if (res == -1) exit(0);
    return res;
}

int main() {
    int n = fastReadInt();
    if (n <= 1) {
        printf("!\n");
        fflush(stdout);
        return 0;
    }

    int stride = n + 1;
    vector<uint8_t> anc((size_t)stride * stride, 0);

    auto setAnc = [&](int u, int v, uint8_t val) {
        anc[(size_t)u * stride + v] = val;
    };
    auto getAnc = [&](int u, int v) -> uint8_t {
        return anc[(size_t)u * stride + v];
    };

    for (int v = 1; v <= n; v++) setAnc(1, v, 1);
    for (int u = 1; u <= n; u++) setAnc(u, u, 1);

    for (int v = 2; v <= n; v++) {
        for (int u = 2; u <= n; u++) {
            if (u == v) continue;
            int res = askPath(u, 1, v);
            setAnc(u, v, (uint8_t)res);
        }
    }

    vector<int> parent(n + 1, 1);
    for (int v = 2; v <= n; v++) {
        int p = 1;
        for (int u = 2; u <= n; u++) {
            if (u == v) continue;
            if (!getAnc(u, v)) continue;      // u not on path(1, v)
            if (getAnc(p, u)) p = u;          // u is deeper than p among ancestors of v
        }
        parent[v] = p;
    }

    printf("!\n");
    for (int v = 2; v <= n; v++) {
        printf("%d %d\n", parent[v], v);
    }
    fflush(stdout);
    return 0;
}