#include <bits/stdc++.h>
using namespace std;

const int N = 1000000;

int spf[N+1];
int omega[N+1];
int f[N+1];

int main() {
    int n;
    scanf("%d", &n);
    vector<int> primes;
    spf[1] = 1;
    omega[1] = 0;
    f[1] = 1;
    for (int i = 2; i <= n; i++) {
        if (!spf[i]) {
            spf[i] = i;
            omega[i] = 1;
            primes.push_back(i);
        }
        for (int p : primes) {
            if (p > spf[i] || (long long)i * p > n) break;
            int j = i * p;
            spf[j] = p;
            omega[j] = omega[i] + 1;
        }
        f[i] = (omega[i] % 2 == 0) ? 1 : -1;
    }
    for (int i = 1; i <= n; i++) {
        printf("%d%c", f[i], " \n"[i == n]);
    }
    return 0;
}