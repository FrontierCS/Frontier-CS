#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>

using namespace std;

typedef long long ll;
typedef __int128_t int128;

ll n;
vector<ll> best_seq;
int128 max_v = 0;

vector<int> primes;
const int SIEVE_LIMIT = 1000100;
vector<bool> is_prime_sieve;

void sieve(int limit) {
    if (!primes.empty()) return;
    is_prime_sieve.assign(limit + 1, true);
    is_prime_sieve[0] = is_prime_sieve[1] = false;
    for (int p = 2; p * p <= limit; ++p) {
        if (is_prime_sieve[p]) {
            for (int i = p * p; i <= limit; i += p)
                is_prime_sieve[i] = false;
        }
    }
    for (int p = 2; p <= limit; ++p) {
        if (is_prime_sieve[p]) {
            primes.push_back(p);
        }
    }
}

ll gcd(ll a, ll b) {
    while (b) {
        a %= b;
        swap(a, b);
    }
    return a;
}

void update_best(const vector<ll>& seq) {
    if (seq.empty()) return;
    int128 current_sum = 0;
    for (ll x : seq) {
        current_sum += x;
    }
    int128 current_v = (int128)seq.size() * current_sum;
    if (current_v > max_v) {
        max_v = current_v;
        best_seq = seq;
    }
}

ll smallest_divisor_greater_than(ll val, ll thres) {
    ll res = -1;
    for (ll i = 1; i * i <= val; ++i) {
        if (val % i == 0) {
            ll d1 = i;
            ll d2 = val / i;
            if (d1 > thres) {
                if (res == -1 || d1 < res) res = d1;
            }
            if (d2 > thres) {
                if (res == -1 || d2 < res) res = d2;
            }
        }
    }
    return res;
}

ll smallest_coprime_greater_than(ll q, ll m_low) {
    if (q == 1) return m_low + 1;
    for (ll m = m_low + 1; ; ++m) {
        if (gcd(m, q) == 1) {
            return m;
        }
    }
}

ll get_spf(ll val) {
    if (val == 1) return 1;
    for (int p : primes) {
        if ((ll)p * p > val) break;
        if (val % p == 0) return p;
    }
    return val;
}

void solve() {
    cin >> n;

    sieve(SIEVE_LIMIT);
    
    // Construction P-mod
    if (n >= 3) {
        vector<ll> seq;
        seq.push_back(2);
        seq.push_back(3);
        if (2 <= n && 3 <= n) {
            for (size_t i = 1; i + 1 < primes.size(); ++i) {
                int128 p1 = primes[i];
                int128 p2 = primes[i+1];
                if (p1 * p2 > n) break;
                seq.push_back(p1 * p2);
            }
            update_best(seq);
        }
    }

    // Smallest Divisor Search
    int L1 = 15, L2 = 250;
    if (n <= 1000) { L1 = (n > 1) ? (n-1) : 1; L2 = n; }
    else if (n <= 100000) { L1 = 30, L2 = 300; }
    
    for (ll a1 = 1; a1 <= L1; ++a1) {
        for (ll a2 = a1 + 1; a2 <= L2; ++a2) {
            if (a1 > n || a2 > n) continue;
            
            vector<ll> current_seq;
            current_seq.push_back(a1);
            current_seq.push_back(a2);

            const int ITER_LIMIT = 400;

            for (int iter_count = 0; iter_count < ITER_LIMIT; ++iter_count) {
                ll a_prev = current_seq[current_seq.size()-2];
                ll a_cur = current_seq.back();
                ll g_prev = gcd(a_prev, a_cur);
                
                if (a_cur > 1 && g_prev >= a_cur / get_spf(a_cur)) {
                    int128 cur_sum_128 = 0;
                    for(ll val : current_seq) cur_sum_128 += val;
                    
                    int current_len = current_seq.size();
                    ll last_term = a_cur;

                    ll gp_len_to_add = 0;
                    if (last_term > 0 && last_term <= n/2) {
                        unsigned __int128 N_128 = n;
                        unsigned __int128 last_term_128 = last_term;
                        unsigned __int128 ratio_128 = N_128/last_term_128;
                        if (ratio_128 > 0)
                            gp_len_to_add = floor(log2((long double)ratio_128));
                    }
                    
                    if (gp_len_to_add > 0) {
                        int128 gp_sum = last_term;
                        int128 power_of_2;

                        if (gp_len_to_add + 1 >= 127) {
                           // This would overflow. Avoid direct computation.
                           // For this problem's constraints, it won't be an issue.
                           // As a safeguard, just approximate V to be huge.
                           power_of_2 = -2; 
                        } else {
                           power_of_2 = ((int128)1 << (gp_len_to_add + 1)) - 1;
                        }
                        
                        gp_sum *= power_of_2;
                        gp_sum -= last_term;
                        
                        cur_sum_128 += gp_sum;
                        current_len += gp_len_to_add;
                    }
                    
                    int128 current_v = (int128)current_len * cur_sum_128;

                    if (current_v > max_v) {
                        vector<ll> final_seq = current_seq;
                        ll term = last_term;
                        for (int j=0; j<gp_len_to_add; ++j) {
                            term *= 2;
                            final_seq.push_back(term);
                        }
                        update_best(final_seq);
                    }
                    goto next_pair;
                }

                ll d = smallest_divisor_greater_than(a_cur, g_prev);
                if (d == -1) d = a_cur;
                
                ll q = a_cur / d;
                ll m_low = a_cur / d;
                ll m = smallest_coprime_greater_than(q, m_low);
                
                int128 a_next_128 = (int128)m * d;
                if (a_next_128 > n) {
                    break;
                }
                ll a_next = a_next_128;
                current_seq.push_back(a_next);
            }
            update_best(current_seq);
            next_pair:;
        }
    }
    
    // Fallback: powers of 2 starting from 1
    if (best_seq.empty()) {
        vector<ll> seq;
        ll cur = 1;
        if (cur <= n) {
            while(true) {
                seq.push_back(cur);
                if (cur > n/2) break;
                cur *= 2;
            }
        }
        update_best(seq);
    }

    cout << best_seq.size() << endl;
    for (size_t i = 0; i < best_seq.size(); ++i) {
        cout << best_seq[i] << (i == best_seq.size() - 1 ? "" : " ");
    }
    cout << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    solve();
    return 0;
}