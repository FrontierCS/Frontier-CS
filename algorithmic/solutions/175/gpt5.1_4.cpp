#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, m;
    if (scanf("%d %d", &n, &m) != 2) return 0;

    vector<int> pos(n + 1, 0), neg(n + 1, 0);

    int a, b, c;
    for (int i = 0; i < m; ++i) {
        if (scanf("%d %d %d", &a, &b, &c) != 3) return 0;

        int x = a;
        if (x > 0) ++pos[x]; else ++neg[-x];
        x = b;
        if (x > 0) ++pos[x]; else ++neg[-x];
        x = c;
        if (x > 0) ++pos[x]; else ++neg[-x];
    }

    for (int i = 1; i <= n; ++i) {
        int v = (pos[i] >= neg[i]) ? 1 : 0;
        if (i > 1) printf(" ");
        printf("%d", v);
    }
    printf("\n");

    return 0;
}