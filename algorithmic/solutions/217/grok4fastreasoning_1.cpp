#include <bits/stdc++.h>
using namespace std;

int main() {
    int N, M;
    scanf("%d %d", &N, &M);
    int L = N * M;
    bool usedd[10001] = {false};
    char exx[10001];
    for (int s = 0; s < M; s++) {
        int P[401];
        int ps = 0;
        int cur = 1;
        while (ps < N) {
            while (cur <= L) {
                if (usedd[cur]) {
                    cur++;
                    continue;
                }
                int k = cur;
                cur++;
                if (ps == 0) {
                    P[ps++] = k;
                    usedd[k] = true;
                    break;
                }
                memset(exx, 0, L + 1);
                for (int j = 0; j < ps; j++) exx[P[j]] = 1;
                exx[k] = 1;
                int qk = L - ps - 1;
                printf("? %d", qk);
                for (int i = 1; i <= L; i++) if (!exx[i]) printf(" %d", i);
                printf("\n");
                fflush(stdout);
                int resp;
                scanf("%d", &resp);
                if (resp == M - 1) {
                    P[ps++] = k;
                    usedd[k] = true;
                    break;
                }
            }
        }
        printf("!");
        for (int j = 0; j < N; j++) printf(" %d", P[j]);
        printf("\n");
        fflush(stdout);
    }
    return 0;
}