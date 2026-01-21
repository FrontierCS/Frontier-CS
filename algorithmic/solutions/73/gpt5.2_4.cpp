#include <bits/stdc++.h>
using namespace std;

static unsigned char S[2005][2005];

int main() {
    int n;
    if (scanf("%d", &n) != 1) return 0;

    vector<int> smaller(n + 2, 0);

    for (int len = 2; len <= n; ++len) {
        for (int l = 1; l + len - 1 <= n; ++l) {
            int r = l + len - 1;
            printf("0 %d %d\n", l, r);
            fflush(stdout);

            int resp;
            if (scanf("%d", &resp) != 1) return 0;
            if (resp < 0) return 0;

            S[l][r] = (unsigned char)(resp & 1);

            int c = (int)S[l][r] ^ (int)S[l + 1][r] ^ (int)S[l][r - 1] ^ (int)S[l + 1][r - 1];
            if (c) ++smaller[l];
            else ++smaller[r];
        }
    }

    printf("1");
    for (int i = 1; i <= n; ++i) printf(" %d", smaller[i] + 1);
    printf("\n");
    fflush(stdout);
    return 0;
}