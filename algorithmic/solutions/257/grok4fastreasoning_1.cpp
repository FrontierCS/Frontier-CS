#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    scanf("%d", &n);
    vector<long long> arr(n + 1);
    int pos = 1;
    while (pos <= n) {
        printf("? %d %d\n", pos, pos);
        fflush(stdout);
        long long v;
        int f;
        scanf("%lld %d", &v, &f);
        int left = pos;
        int right = n;
        int e = pos;
        while (left <= right) {
            int mid = left + (right - left) / 2;
            printf("? %d %d\n", pos, mid);
            fflush(stdout);
            long long mx;
            int mf;
            scanf("%lld %d", &mx, &mf);
            if (mx == v && mf == mid - pos + 1) {
                e = mid;
                left = mid + 1;
            } else {
                right = mid - 1;
            }
        }
        for (int i = pos; i <= e; i++) {
            arr[i] = v;
        }
        pos = e + 1;
    }
    printf("! ");
    for (int i = 1; i <= n; i++) {
        if (i > 1) printf(" ");
        printf("%lld", arr[i]);
    }
    printf("\n");
    fflush(stdout);
    return 0;
}