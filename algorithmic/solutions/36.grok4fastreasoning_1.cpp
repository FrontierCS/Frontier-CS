#include <bits/stdc++.h>
using namespace std;

int main() {
    long long k = 1000000LL;
    printf("0 %lld", k);
    for (long long i = 1; i <= k; i++) {
        printf(" %lld", i);
    }
    printf("\n");
    fflush(stdout);
    long long c;
    scanf("%lld", &c);
    if (c == 0) {
        printf("1 %lld\n", 1000001LL);
        fflush(stdout);
        return 0;
    }
    bool found = false;
    long long nn = 2;
    for (long long q = 1; q <= k / 2; q++) {
        long long num = 2LL * (q * k - c);
        long long den = q * (q + 1LL);
        if (num % den == 0) {
            long long candidate = num / den;
            if (candidate >= 2 && candidate <= 1000000000LL) {
                if (k / candidate == q) {
                    nn = candidate;
                    found = true;
                    break;
                }
            }
        }
    }
    printf("1 %lld\n", nn);
    fflush(stdout);
    return 0;
}