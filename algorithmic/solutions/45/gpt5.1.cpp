#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, k;
    long long m;
    double eps;
    if (scanf("%d %lld %d %lf", &n, &m, &k, &eps) != 4) {
        return 0;
    }

    int u, v;
    for (long long i = 0; i < m; ++i) {
        if (scanf("%d %d", &u, &v) != 2) break;
    }

    if (n <= 0) return 0;

    long long ideal = ( (long long)n + k - 1 ) / k;

    for (int i = 1; i <= n; ++i) {
        int part = (int)(((long long)(i - 1) / ideal) + 1);
        if (part > k) part = k;
        printf("%d%c", part, (i == n ? '\n' : ' '));
    }

    return 0;
}