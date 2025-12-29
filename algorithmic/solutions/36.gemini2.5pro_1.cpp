#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <random>
#include <chrono>

using namespace std;

long long query(const vector<long long>& v) {
    if (v.empty()) {
        return 0;
    }
    cout << "0 " << v.size();
    for (long long x : v) {
        cout << " " << x;
    }
    cout << endl;
    long long collisions;
    cin >> collisions;
    return collisions;
}

void answer(long long n) {
    cout << "1 " << n << endl;
}

mt19937_64 rng(chrono::steady_clock::now().time_since_epoch().count());

const int S = 30000;
vector<int> primes;
vector<bool> is_prime_sieve_small;

void sieve(int limit) {
    is_prime_sieve_small.assign(limit + 1, true);
    is_prime_sieve_small[0] = is_prime_sieve_small[1] = false;
    for (int p = 2; p * p <= limit; ++p) {
        if (is_prime_sieve_small[p]) {
            for (int i = p * p; i <= limit; i += p)
                is_prime_sieve_small[i] = false;
        }
    }
    for (int p = 2; p <= limit; ++p) {
        if (is_prime_sieve_small[p]) {
            primes.push_back(p);
        }
    }
}

long long power(long long base, int exp) {
    __int128 res = 1;
    __int128 b = base;
    while (exp > 0) {
        if (exp % 2 == 1) res *= b;
        b *= b;
        exp /= 2;
        if (res > 2000000000LL || (b > 2000000000LL && exp > 0)) return 2000000000LL;
    }
    return (long long)res;
}


int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    sieve(S);

    vector<long long> initial_query_vec(S);
    iota(initial_query_vec.begin(), initial_query_vec.end(), 1);
    long long initial_collisions = query(initial_query_vec);

    if (initial_collisions > 0) {
        long long l = 1, r = S;
        while (l < r) {
            long long mid = l + (r - l) / 2;
            vector<long long> v(mid);
            iota(v.begin(), v.end(), 1);
            if (query(v) > 0) {
                r = mid;
            } else {
                l = mid + 1;
            }
        }
        answer(l - 1);
    } else {
        long long P = 1;
        for (int p : primes) {
            int max_exp = 0;
            if (p > 1 && log(1000000000.0) / log(p) > 0) max_exp = log(1000000000.0) / log(p);
            
            int low_exp = 0, high_exp = max_exp, p_exp = 0;
            while(low_exp <= high_exp) {
                int mid_exp = low_exp + (high_exp - low_exp) / 2;
                if (mid_exp == 0) {
                    low_exp = mid_exp + 1;
                    continue;
                }
                long long p_power = power(p, mid_exp);

                if (p_power > 1000000000LL) {
                    high_exp = mid_exp - 1;
                    continue;
                }

                if(query({1, 1 + p_power}) == 1) {
                    p_exp = mid_exp;
                    low_exp = mid_exp + 1;
                } else {
                    high_exp = mid_exp - 1;
                }
            }
            if (p_exp > 0) {
                 P *= power(p, p_exp);
            }
        }

        const int M = 100000;
        vector<double> q_ests;
        for(int i = 0; i < 5; ++i) {
            vector<long long> v(M);
            uniform_int_distribution<long long> distrib(1, 1000000000000000000LL);
            for(int j = 0; j < M; ++j) {
                v[j] = distrib(rng);
            }
            long long c = query(v);
            if (c > 0) {
                q_ests.push_back((double)M * (M - 1) / (2.0 * c * P));
            }
        }

        long long q_est = 1000000000LL / P;
        if (!q_ests.empty()) {
            sort(q_ests.begin(), q_ests.end());
            q_est = q_ests[q_ests.size() / 2];
        }

        long long final_q = -1;

        vector<long long> widths = {50000, 200000, 500000, 2000000, 1000000000LL};
        for(long long width : widths) {
            if (final_q != -1) break;
            long long q_min = max((long long)S, q_est - width);
            long long q_max = min(1000000000LL / P, q_est + width);
            if(q_min > q_max) continue;

            vector<bool> is_prime_range(q_max - q_min + 1, true);
            for (long long p : primes) {
                if (p * p > q_max) break;
                long long start = max(p * p, (q_min + p - 1) / p * p);
                for (long long j = start; j <= q_max; j += p) {
                    if (j >= q_min) {
                        is_prime_range[j - q_min] = false;
                    }
                }
            }
            if (q_min <= 1 && q_max >= 1) {
                if(q_min == 0) is_prime_range[1] = is_prime_range[0] = false;
                else is_prime_range[1-q_min] = false;
            }


            for (long long q_cand = q_min; q_cand <= q_max; ++q_cand) {
                if (q_cand < S) continue;
                if (is_prime_range[q_cand - q_min]) {
                    if(query({1, 1 + P * q_cand}) == 1) {
                        final_q = q_cand;
                        break;
                    }
                }
            }
        }

        if (final_q != -1) {
            answer(P * final_q);
        } else {
            vector<long long> v_q_check;
            for(int i=0; i < S; ++i) v_q_check.push_back(1 + (long long)i * P);
            if (query(v_q_check) > 0) {
                 answer(P);
            } else {
                 answer(P);
            }
        }
    }

    return 0;
}