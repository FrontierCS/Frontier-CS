#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    if (scanf("%d", &n) != 1) return 0;

    vector<vector<unsigned char>> P(n + 3, vector<unsigned char>(n + 3, 0));

    for (int l = 1; l <= n; l++) {
        for (int r = l + 1; r <= n; r++) {
            printf("0 %d %d\n", l, r);
            fflush(stdout);
            int ans;
            if (scanf("%d", &ans) != 1) return 0;
            P[l][r] = (unsigned char)(ans & 1);
        }
    }

    vector<int> win(n + 2, 0);
    for (int i = 1; i <= n; i++) {
        for (int j = i + 1; j <= n; j++) {
            unsigned char x = (unsigned char)(P[i][j] ^ P[i + 1][j] ^ P[i][j - 1] ^ P[i + 1][j - 1]);
            if (x) win[i]++; else win[j]++;
        }
    }

    printf("1");
    for (int i = 1; i <= n; i++) {
        printf(" %d", win[i] + 1);
    }
    printf("\n");
    fflush(stdout);
    return 0;
}