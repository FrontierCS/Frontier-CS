#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    scanf("%d", &n);
    vector<vector<int>> S(n + 1, vector<int>(n + 1, 0));
    for (int len = 2; len <= n; ++len) {
        for (int l = 1; l <= n - len + 1; ++l) {
            int r = l + len - 1;
            printf("? %d %d\n", l, r);
            fflush(stdout);
            int res;
            scanf("%d", &res);
            S[l][r] = res;
        }
    }
    vector<vector<int>> X(n + 1, vector<int>(n + 1, 0));
    for (int r = 2; r <= n; ++r) {
        vector<int> P(r + 1, 0);
        P[r] = 0;
        for (int l = 1; l < r; ++l) {
            int s_prev = S[l][r - 1];
            P[l] = S[l][r] ^ s_prev;
        }
        for (int l = 1; l < r; ++l) {
            X[l][r] = P[l] ^ P[l + 1];
        }
    }
    vector<int> positions(n);
    for (int i = 0; i < n; ++i) {
        positions[i] = i + 1;
    }
    sort(positions.begin(), positions.end(), [&](int a, int b) -> bool {
        if (a < b) {
            return X[a][b] == 0;
        } else {
            return X[b][a] == 1;
        }
    });
    vector<int> perm(n + 1);
    for (int rank = 1; rank <= n; ++rank) {
        int pos = positions[rank - 1];
        perm[pos] = rank;
    }
    printf("!");
    for (int i = 1; i <= n; ++i) {
        printf(" %d", perm[i]);
    }
    printf("\n");
    fflush(stdout);
    return 0;
}