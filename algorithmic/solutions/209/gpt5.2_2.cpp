#include <bits/stdc++.h>
using namespace std;

using int64 = long long;
using i128 = __int128_t;

static inline long long sphereCount(int depth, int dist, int h) {
    // number of nodes at exact distance 'dist' from a node at depth 'depth'
    long long total = 0;
    int down = (h - 1) - depth;

    // k = 0: go down only within own subtree
    if (dist <= down) total += (1LL << dist);

    int maxk = min(depth, dist);
    for (int k = 1; k <= maxk; k++) {
        int rem = dist - k;
        if (rem == 0) {
            // ancestor itself
            total += 1;
        } else {
            // go down into sibling subtree of the k-th ancestor
            int siblingRootDepth = depth - k + 1;
            int height = (h - 1) - siblingRootDepth; // remaining downward edges possible inside sibling subtree
            if (rem - 1 <= height) total += (1LL << (rem - 1));
        }
    }
    return total;
}

static inline void print_i128(i128 x) {
    if (x == 0) {
        putchar('0');
        return;
    }
    if (x < 0) {
        putchar('-');
        x = -x;
    }
    char s[64];
    int n = 0;
    while (x > 0) {
        int digit = (int)(x % 10);
        s[n++] = char('0' + digit);
        x /= 10;
    }
    for (int i = n - 1; i >= 0; --i) putchar(s[i]);
}

int main() {
    int h;
    if (scanf("%d", &h) != 1) return 0;

    int n = (1 << h) - 1;
    vector<int> ds;
    ds.reserve(h);
    for (int d = h - 1; d <= 2 * h - 2; d++) ds.push_back(d); // size h

    vector<vector<long long>> M(h, vector<long long>(h, 0));
    for (int i = 0; i < h; i++) {
        int d = ds[i];
        for (int t = 0; t < h; t++) M[i][t] = sphereCount(t, d, h);
    }

    vector<i128> A(h, 0);
    for (int i = 0; i < h; i++) {
        int d = ds[i];
        i128 sum = 0;
        for (int u = 1; u <= n; u++) {
            printf("? %d %d\n", u, d);
            fflush(stdout);
            long long r;
            if (scanf("%lld", &r) != 1) return 0;
            if (r == -1) return 0;
            sum += (i128)r;
        }
        A[i] = sum;
    }

    vector<i128> F(h, 0);
    for (int i = h - 1; i >= 0; i--) {
        i128 rhs = A[i];
        for (int t = i + 1; t < h; t++) rhs -= (i128)M[i][t] * F[t];
        long long diag = M[i][i];
        if (diag == 0) return 0;
        F[i] = rhs / (i128)diag;
    }

    i128 S = 0;
    for (int i = 0; i < h; i++) S += F[i];

    printf("! ");
    print_i128(S);
    printf("\n");
    fflush(stdout);
    return 0;
}