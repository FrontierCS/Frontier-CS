#include <cstdio>
#include <vector>
using namespace std;

typedef long long ll;

ll powmod(ll a, ll b, ll m) {
    ll res = 1;
    a %= m;
    while (b) {
        if (b & 1) res = res * a % m;
        a = a * a % m;
        b >>= 1;
    }
    return res;
}

int legendre(int a, int p) {
    ll res = powmod(a, (p - 1) / 2, p);
    return (res == 1) ? 1 : -1;
}

int main() {
    int n;
    scanf("%d", &n);

    // linear sieve for smallest prime factor and primes up to n
    vector<int> spf(n + 1);
    vector<int> primes;
    for (int i = 2; i <= n; ++i) {
        if (!spf[i]) {
            spf[i] = i;
            primes.push_back(i);
        }
        for (int p : primes) {
            if (p > spf[i] || i * p > n) break;
            spf[i * p] = p;
        }
    }

    // first 10 primes greater than n
    vector<int> candidates;
    for (int p = n + 1; candidates.size() < 10; ++p) {
        bool is_prime = true;
        for (int d = 2; d * d <= p; ++d) {
            if (p % d == 0) {
                is_prime = false;
                break;
            }
        }
        if (is_prime) candidates.push_back(p);
    }

    vector<int> best_f(n + 1);
    ll best_max = 1LL << 60;

    for (int P : candidates) {
        vector<int> f(n + 1, 0);
        f[1] = 1;
        for (int p : primes) f[p] = legendre(p, P);
        for (int i = 2; i <= n; ++i) {
            if (f[i] == 0) {
                int p = spf[i];
                int j = i / p;
                f[i] = f[p] * f[j];
            }
        }
        ll sum = 0, cur_max = 0;
        for (int i = 1; i <= n; ++i) {
            sum += f[i];
            if (sum > cur_max) cur_max = sum;
            if (-sum > cur_max) cur_max = -sum;
        }
        if (cur_max < best_max) {
            best_max = cur_max;
            best_f = f;
        }
    }

    for (int i = 1; i <= n; ++i) {
        printf("%d%c", best_f[i], " \n"[i == n]);
    }
    return 0;
}