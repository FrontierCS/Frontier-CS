#include <iostream>

const int N = 1000000;
int spf[N + 1];
int f[N + 1];

void sieve() {
    for (int i = 0; i <= N; ++i) {
        spf[i] = i;
    }
    for (int i = 2; i * i <= N; ++i) {
        if (spf[i] == i) { // i is prime
            for (int j = i * i; j <= N; j += i) {
                if (spf[j] == j) {
                    spf[j] = i;
                }
            }
        }
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n = N;

    sieve();

    f[1] = 1;
    long long current_sum = 1;

    for (int i = 2; i <= n; ++i) {
        if (spf[i] == i) { // i is prime
            if (current_sum > 0) {
                f[i] = -1;
            } else {
                f[i] = 1;
            }
        } else { // i is composite
            f[i] = f[spf[i]] * f[i / spf[i]];
        }
        current_sum += f[i];
    }
    
    for (int i = 1; i <= n; ++i) {
        std::cout << f[i] << (i == n ? "" : " ");
    }
    std::cout << "\n";

    return 0;
}