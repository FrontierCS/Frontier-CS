#include <bits/stdc++.h>
using namespace std;

int main() {
    int n, m;
    while (scanf("%d %d", &n, &m) == 2) {
        vector<float> w(n, 1.0f);
        char s[1001];
        for (int t = 0; t < m; ++t) {
            scanf("%s", s);
            float sum0 = 0, sum1 = 0;
            for (int i = 0; i < n; ++i) {
                if (s[i] == '0') sum0 += w[i];
                else sum1 += w[i];
            }
            int pred = (sum1 > sum0) ? 1 : 0;
            printf("%d\n", pred);
            fflush(stdout);
            int y;
            scanf("%d", &y);
            float total = 0.0f;
            for (int i = 0; i < n; ++i) {
                if (s[i] != y + '0') {
                    w[i] *= 0.5f;
                }
                total += w[i];
            }
            // renormalize
            if (total > 0) {
                for (int i = 0; i < n; ++i) {
                    w[i] /= total;
                }
            }
        }
    }
    return 0;
}