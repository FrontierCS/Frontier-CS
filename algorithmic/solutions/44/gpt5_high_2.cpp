#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N;
    if (!(cin >> N)) return 0;
    long long x, y;
    for (int i = 0; i < N; ++i) {
        cin >> x >> y; // Coordinates are not used for constructing the route
    }

    vector<char> isPrime(N, true);
    if (N > 0) isPrime[0] = false;
    if (N > 1) isPrime[1] = false;
    for (int i = 2; (long long)i * i < N; ++i) {
        if (isPrime[i]) {
            for (int j = i * i; j < N; j += i) isPrime[j] = false;
        }
    }

    vector<int> primes, nonprimes;
    primes.reserve(N);
    nonprimes.reserve(N);
    for (int i = 1; i < N; ++i) {
        if (isPrime[i]) primes.push_back(i);
        else nonprimes.push_back(i);
    }

    int reqLeft = N / 10; // Number of steps t in [1..N] with t % 10 == 0
    vector<int> P(N + 1);
    P[0] = 0;

    size_t pPtr = 0, npPtr = 0;
    for (int j = 1; j <= N - 1; ++j) {
        bool forced = ((j + 1) % 10 == 0);
        if (forced) {
            if (pPtr < primes.size()) {
                P[j] = primes[pPtr++];
            } else {
                // No primes left; must use a non-prime
                if (npPtr < nonprimes.size()) P[j] = nonprimes[npPtr++];
                else {
                    // Fallback (shouldn't happen unless N small weird cases)
                    P[j] = 1; // placeholder; but ideally unreachable
                }
            }
            reqLeft--;
        } else {
            size_t pLeft = primes.size() - pPtr;
            bool canUsePrime = (pLeft > (size_t)reqLeft);

            if (!canUsePrime || pPtr >= primes.size()) {
                // Use non-prime if available
                if (npPtr < nonprimes.size()) P[j] = nonprimes[npPtr++];
                else if (pPtr < primes.size()) P[j] = primes[pPtr++];
                else P[j] = 1; // unreachable
            } else if (npPtr >= nonprimes.size()) {
                // Only primes left
                P[j] = primes[pPtr++];
            } else {
                // Choose the smaller ID to keep order smooth
                if (primes[pPtr] < nonprimes[npPtr]) P[j] = primes[pPtr++];
                else P[j] = nonprimes[npPtr++];
            }
        }
    }

    P[N] = 0;

    cout << N + 1 << '\n';
    for (int i = 0; i <= N; ++i) {
        cout << P[i] << '\n';
    }

    return 0;
}