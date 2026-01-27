#include <bits/stdc++.h>
using namespace std;

static inline int ask(int l, int r) {
    printf("0 %d %d\n", l, r);
    fflush(stdout);
    int ans;
    if (scanf("%d", &ans) != 1) exit(0);
    if (ans == -1) exit(0);
    return ans & 1;
}

int main() {
    int n;
    if (scanf("%d", &n) != 1) return 0;

    vector<int> out(n + 1, 0);
    vector<unsigned char> prev(n + 2, 0), curr(n + 2, 0), B(n + 3, 0);

    for (int r = 2; r <= n; r++) {
        for (int l = 1; l < r; l++) curr[l] = (unsigned char)ask(l, r);
        curr[r] = 0;

        for (int l = 1; l < r; l++) B[l] = (unsigned char)(curr[l] ^ prev[l]);
        B[r] = 0;

        for (int l = 1; l < r; l++) {
            unsigned char a = (unsigned char)(B[l] ^ B[l + 1]); // [p_l > p_r]
            if (a) out[l]++;
            else out[r]++;
        }

        for (int l = 1; l < r; l++) prev[l] = curr[l];
        prev[r] = 0;
    }

    printf("1");
    for (int i = 1; i <= n; i++) printf(" %d", out[i] + 1);
    printf("\n");
    fflush(stdout);
    return 0;
}