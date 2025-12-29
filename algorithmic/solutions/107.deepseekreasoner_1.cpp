#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <cassert>

using namespace std;

typedef long long ll;

const ll MAX_X = 1000000000LL;
const ll MAX_Q = 1000000000000000000LL;
const int SMALL_PRIME_LIMIT = 30; // we test first 30 primes individually
const int THRESHOLD_U = 350;      // if U <= THRESHOLD_U, test all primes up to U

vector<int> primes;
vector<bool> is_prime;

void sieve(int n) {
    is_prime.assign(n + 1, true);
    is_prime[0] = is_prime[1] = false;
    for (int i = 2; i <= n; ++i) {
        if (is_prime[i]) {
            primes.push_back(i);
            for (int j = i + i; j <= n; j += i) {
                is_prime[j] = false;
            }
        }
    }
}

// compute Q = p^k with p^k > MAX_X and p^k <= MAX_Q
ll get_prime_power(int p) {
    ll res = 1;
    while (res <= MAX_X) {
        if (res > MAX_Q / p) {
            // multiplying would overflow
            if (res == 1) {
                // p itself might be > MAX_X and <= MAX_Q
                res = p;
            }
            break;
        }
        res *= p;
    }
    return res;
}

// extract exponent e from g = p^e
int get_exponent(ll g, int p) {
    int e = 0;
    while (g % p == 0) {
        g /= p;
        e++;
    }
    return e;
}

ll powll(ll a, int e) {
    ll res = 1;
    for (int i = 0; i < e; ++i) res *= a;
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    sieve(50000); // primes up to 50000 enough for sqrt(1e9)

    int T;
    cin >> T;

    // indices of the first SMALL_PRIME_LIMIT primes
    int small_end = 0;
    while (small_end < (int)primes.size() && primes[small_end] <= 113) {
        small_end++;
    }
    // ensure we have at least SMALL_PRIME_LIMIT primes
    if (small_end < SMALL_PRIME_LIMIT) {
        // not enough primes, but our sieve gives plenty
        small_end = SMALL_PRIME_LIMIT;
    }

    for (int game = 0; game < T; ++game) {
        ll D = 1;          // product of found prime powers
        ll d = 1;          // divisor count from found primes
        int used = 0;
        vector<bool> found(primes.size(), false);

        // ---------- Phase A: test first SMALL_PRIME_LIMIT primes ----------
        for (int i = 0; i < small_end && used < 100; ++i) {
            int p = primes[i];
            ll Q = get_prime_power(p);
            cout << "0 " << Q << endl;
            cout.flush();
            ll g;
            cin >> g;
            used++;
            if (g > 1) {
                int e = get_exponent(g, p);
                D *= powll(p, e);
                d *= (e + 1);
                found[i] = true;
            }
        }

        // ---------- Prepare for next phase ----------
        ll U = MAX_X / D;               // upper bound for remaining part
        int start_idx = small_end;      // first prime not tested individually

        // ---------- Case 1: U is small ----------
        if (U <= THRESHOLD_U) {
            for (int i = start_idx; i < (int)primes.size() && used < 100; ++i) {
                int p = primes[i];
                if (p > U) break;
                if (found[i]) continue;
                ll Q = get_prime_power(p);
                cout << "0 " << Q << endl;
                cout.flush();
                ll g;
                cin >> g;
                used++;
                if (g > 1) {
                    int e = get_exponent(g, p);
                    D *= powll(p, e);
                    d *= (e + 1);
                    found[i] = true;
                    U = MAX_X / D;   // update U
                }
            }
            // after scanning all primes up to U, remaining part must be 1
            // because any prime factor would be <= U and we tested them all.
            ll d_res = 1;
            d *= d_res;
        }
        // ---------- Case 2: U is large ----------
        else {
            ll sqrtU = sqrtl(U);
            int idx = start_idx;
            bool stop = false;

            while (used < 100 && idx < (int)primes.size() && !stop) {
                // if the next prime is > sqrtU, we can stop
                if (primes[idx] > sqrtU) {
                    stop = true;
                    break;
                }

                // form a batch: product of consecutive primes not found, staying within max_prod
                ll max_prod = MAX_Q / D;
                ll batch_prod = 1;
                vector<int> batch_indices;
                while (idx < (int)primes.size() && !found[idx]) {
                    int p = primes[idx];
                    if (batch_prod > max_prod / p) break;
                    batch_prod *= p;
                    batch_indices.push_back(idx);
                    idx++;
                }

                if (batch_indices.empty()) break; // no more primes to test

                // query the batch
                ll Q = D * batch_prod;
                cout << "0 " << Q << endl;
                cout.flush();
                ll g;
                cin >> g;
                used++;

                if (g > D) {
                    ll h = g / D; // gcd(remaining, batch_prod)
                    for (int j : batch_indices) {
                        if (used >= 100) break;
                        int p = primes[j];
                        if (h % p == 0) {
                            // p divides the remaining part
                            ll Qp = get_prime_power(p);
                            cout << "0 " << Qp << endl;
                            cout.flush();
                            ll gp;
                            cin >> gp;
                            used++;
                            if (gp > 1) {
                                int e = get_exponent(gp, p);
                                D *= powll(p, e);
                                d *= (e + 1);
                                found[j] = true;
                                // update U and sqrtU
                                U = MAX_X / D;
                                sqrtU = sqrtl(U);
                                // adjust max_prod for next batches
                                max_prod = MAX_Q / D;
                            }
                        }
                    }
                }

                // after processing batch, check if we should stop because next prime > sqrtU
                if (idx < (int)primes.size() && primes[idx] > sqrtU) {
                    stop = true;
                }
            }

            // estimate contribution of remaining part
            ll d_res;
            if (U == 1) {
                d_res = 1;
            } else if (stop) {
                // we have tested all primes up to sqrtU, so remaining part is either 1 or a prime > sqrtU
                d_res = 2;
            } else {
                // ran out of queries before reaching sqrtU
                d_res = 4;
            }
            d *= d_res;
        }

        // output answer for this game
        cout << "1 " << d << endl;
        cout.flush();
    }

    return 0;
}