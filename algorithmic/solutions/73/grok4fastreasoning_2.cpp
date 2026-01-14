#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    scanf("%d", &n);
    vector<vector<int>> par(n + 1, vector<int>(n + 1, 0));
    for (int l = 1; l <= n; ++l) {
        for (int r = l + 1; r <= n; ++r) {
            printf("0 %d %d\n", l, r);
            fflush(stdout);
            int res;
            scanf("%d", &res);
            par[l][r] = res;
        }
    }
    vector<vector<int>> inv(n + 1, vector<int>(n + 1, 0));
    for (int j = 2; j <= n; ++j) {
        int prev_u = 0;
        for (int i = j - 1; i >= 1; --i) {
            int u = par[i][j] ^ par[i][j - 1];
            inv[i][j] = u ^ prev_u;
            prev_u = u;
        }
    }
    vector<int> p(n + 1);
    for (int k = 1; k <= n; ++k) {
        int smaller = 0;
        for (int m = 1; m <= n; ++m) {
            if (m == k) continue;
            if (m < k) {
                if (inv[m][k] == 0) ++smaller;
            } else {
                if (inv[k][m] == 1) ++smaller;
            }
        }
        p[k] = smaller + 1;
    }
    printf("1");
    for (int i = 1; i <= n; ++i) {
        printf(" %d", p[i]);
    }
    printf("\n");
    fflush(stdout);
    return 0;
}