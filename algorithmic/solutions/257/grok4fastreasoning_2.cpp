#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    scanf("%d", &n);
    vector<int> a(n + 1);
    int pos = 1;
    while (pos <= n) {
        int low = pos - 1;
        int high = n;
        int run_val = -1;
        while (low < high) {
            int mid = low + (high - low + 1) / 2;
            printf("? %d %d\n", pos, mid);
            fflush(stdout);
            int x, f;
            scanf("%d %d", &x, &f);
            int qlen = mid - pos + 1;
            if (f == qlen) {
                if (run_val == -1) run_val = x;
                low = mid;
            } else {
                high = mid - 1;
            }
        }
        int endd = low;
        if (run_val == -1) {
            // Fallback, though shouldn't happen
            printf("? %d %d\n", pos, pos);
            fflush(stdout);
            int x, f;
            scanf("%d %d", &x, &f);
            run_val = x;
        }
        for (int i = pos; i <= endd; ++i) {
            a[i] = run_val;
        }
        pos = endd + 1;
    }
    printf("!");
    for (int i = 1; i <= n; ++i) {
        printf(" %d", a[i]);
    }
    printf("\n");
    fflush(stdout);
    return 0;
}