#include <iostream>
#include <vector>
#include <unordered_map>
#include <cstdlib>

using namespace std;

vector<int> primes;

void generate_primes(int limit) {
    vector<bool> is_prime(limit + 1, true);
    is_prime[0] = is_prime[1] = false;
    for (int i = 2; i <= limit; ++i) {
        if (is_prime[i]) {
            primes.push_back(i);
            if (i * i <= limit) {
                for (int j = i * i; j <= limit; j += i) {
                    is_prime[j] = false;
                }
            }
        }
    }
}

int query(int v, long long x) {
    cout << "? " << v << " " << x << endl;
    int res;
    cin >> res;
    return res;
}

void solve_one() {
    const long long BIG = 1000000;
    int c = query(1, BIG);
    const int m = 1000;
    unordered_map<int, int> baby;  // vertex -> step
    baby[c] = 0;
    long long d = -1;

    // Baby steps
    for (int i = 1; i < m; ++i) {
        int r = query(c, i);
        if (baby.count(r)) {
            d = i - baby[r];
            break;
        }
        baby[r] = i;
    }

    // Giant steps if not found yet
    if (d == -1) {
        for (int k = 1; ; ++k) {
            long long x = 1LL * k * m;
            int r = query(c, x);
            if (baby.count(r)) {
                int j = baby[r];
                d = x - j;
                break;
            }
            // Safety: should not happen for s ≤ 10^6
            if (k > 2000) {
                break;
            }
        }
    }

    // Factor d to obtain its prime factors
    vector<long long> prime_factors;
    long long temp = d;
    for (int p : primes) {
        if (1LL * p * p > temp) break;
        if (temp % p == 0) {
            prime_factors.push_back(p);
            while (temp % p == 0) temp /= p;
        }
    }
    if (temp > 1) prime_factors.push_back(temp);

    // Reduce d to the true cycle length s
    long long s_candidate = d;
    for (long long p : prime_factors) {
        while (s_candidate % p == 0) {
            long long candidate = s_candidate / p;
            if (candidate == 0) break;
            int r = query(c, candidate);
            if (r == c) {
                s_candidate = candidate;
            } else {
                break;
            }
        }
    }

    cout << "! " << s_candidate << endl;
    int response;
    cin >> response;
    if (response == -1) {
        exit(0);
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    generate_primes(1010);
    int n;
    cin >> n;
    for (int i = 0; i < n; ++i) {
        solve_one();
    }
    return 0;
}