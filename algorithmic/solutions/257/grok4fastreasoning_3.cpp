#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    scanf("%d", &n);
    vector<int> arr(n + 1);
    int cur = 1;
    while (cur <= n) {
        int v, ff;
        printf("? %d %d\n", cur, cur);
        fflush(stdout);
        scanf("%d %d", &v, &ff);
        int max_len = 1;
        int lo = 2;
        int hi = n - cur + 1;
        while (lo <= hi) {
            int mid = lo + (hi - lo) / 2;
            int r_pos = cur + mid - 1;
            int mx, mf;
            printf("? %d %d\n", cur, r_pos);
            fflush(stdout);
            scanf("%d %d", &mx, &mf);
            if (mx == v && mf == mid) {
                max_len = mid;
                lo = mid + 1;
            } else {
                hi = mid - 1;
            }
        }
        for (int j = cur; j < cur + max_len; j++) {
            arr[j] = v;
        }
        cur += max_len;
    }
    printf("! ");
    for (int i = 1; i <= n; i++) {
        printf("%d ", arr[i]);
    }
    printf("\n");
    fflush(stdout);
    return 0;
}