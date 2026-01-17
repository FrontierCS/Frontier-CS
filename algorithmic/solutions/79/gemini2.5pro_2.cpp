#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <random>
#include <algorithm>
#include <chrono>

// Using __int128 for modular multiplication
using int128 = __int128;

long long n;

long long power(long long base, long long exp) {
    long long res = 1;
    base %= n;
    while (exp > 0) {
        if (exp % 2 == 1) res = (int128)res * base % n;
        base = (int128)base * base % n;
        exp /= 2;
    }
    return res;
}

long long power_ull(long long base, unsigned long long exp) {
    long long res = 1;
    base %= n;
    while (exp > 0) {
        if (exp % 2 == 1) res = (int128)res * base % n;
        base = (int128)base * base % n;
        exp /= 2;
    }
    return res;
}

long long power_mod(long long base, long long exp, long long modulus) {
    long long res = 1;
    base %= modulus;
    while (exp > 0) {
        if (exp % 2 == 1) res = (int128)res * base % modulus;
        base = (int128)base * base % modulus;
        exp /= 2;
    }
    return res;
}

long long gcd(long long a, long long b) {
    return b == 0 ? a : gcd(b, a % b);
}

unsigned long long ugcd(unsigned long long a, unsigned long long b) {
    return b == 0 ? a : ugcd(b, a % b);
}

namespace PollardRho {
    std::mt19937_64 rng(1337);

    long long pollard(long long num) {
        if (num % 2 == 0) return 2;
        if (num % 3 == 0) return 3;
        
        long long x = rng() % (num - 2) + 2;
        long long y = x;
        long long c = rng() % (num - 1) + 1;
        long long d = 1;

        while (d == 1) {
            x = (power_mod(x, 2, num) + c);
            if(x >= num) x -= num;

            y = (power_mod(y, 2, num) + c);
            if(y >= num) y -= num;
            y = (power_mod(y, 2, num) + c);
            if(y >= num) y -= num;
            
            d = gcd(std::abs(x - y), num);

            if (d == num) { 
                x = rng() % (num - 2) + 2;
                y = x;
                c = rng() % (num - 1) + 1;
                d = 1;
            }
        }
        return d;
    }
}

int bits(long long x) {
    if (x == 0) return 0;
    return 64 - __builtin_clzll(x);
}

long long query(long long a) {
    std::cout << "? " << a << std::endl;
    long long time;
    std::cin >> time;
    return time;
}


double avg_bits_p1 = 0;

double predict_time(long long a, unsigned long long d_prefix, int k, int popcnt_rem) {
    double cost = 0;
    long long r = 1;

    std::vector<long long> a_powers(60);
    a_powers[0] = a;
    for(int i = 1; i < 60; ++i) {
        a_powers[i] = (int128)a_powers[i-1] * a_powers[i-1] % n;
    }
    
    for (int i = 0; i < k; ++i) {
        cost += (long long)(bits(a_powers[i]) + 1) * (bits(a_powers[i]) + 1);
        if ((d_prefix >> i) & 1) {
            cost += (long long)(bits(r) + 1) * (bits(a_powers[i]) + 1);
            r = (int128)r * a_powers[i] % n;
        }
    }

    for (int i = k; i < 60; ++i) {
        cost += (long long)(bits(a_powers[i]) + 1) * (bits(a_powers[i]) + 1);
        if (60 - i > 0 && popcnt_rem > 0) {
            double prob_one = (double)popcnt_rem / (60 - i);
            cost += prob_one * (avg_bits_p1) * (bits(a_powers[i]) + 1);
        }
    }
    return cost;
}


int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> n;

    long long p = PollardRho::pollard(n);
    long long q = n / p;
    if (p > q) std::swap(p, q);

    unsigned long long p_m_1 = p - 1;
    unsigned long long q_m_1 = q - 1;
    unsigned long long m = p_m_1 / ugcd(p_m_1, q_m_1) * q_m_1;

    int S = 0;
    if (m > 0) {
        S = __builtin_ctzll(m);
    }
    unsigned long long T_odd = m >> S;

    std::mt19937_64 rng(std::chrono::steady_clock::now().time_since_epoch().count());
    
    long long g_base;
    while (true) {
        g_base = rng() % (n - 2) + 2;
        if (gcd(g_base, n) != 1) continue;
        long long temp = power_ull(g_base, m >> 1);
        if (temp != 1) break;
    }

    long long g_pow2 = power_ull(g_base, T_odd);
    
    unsigned long long d = 1;
    
    long long t_obs_1 = query(n - 1);
    long long cost_base_1 = (long long)(bits(n - 1) + 1) * (bits(n - 1) + 1) + 2LL * (bits(n - 1) + 1);
    long long r_fixed_bits_p1_1 = bits(n-1)+1;
    long long s1 = (t_obs_1 - cost_base_1 - 4LL * 59) / (2LL * r_fixed_bits_p1_1);
    
    std::vector<long long> s(S + 1);
    s[0] = s1 + 1;
    s[1] = s1;

    for (int k = 2; k <= S; ++k) {
        long long a = power_ull(g_pow2, 1ULL << (S-k));
        long long t_obs_k = query(a);
        
        // H0: d_{k-1}=0
        unsigned long long d_h0 = d;
        long long s_k_h0 = s[k-1];
        long long cost_less_k_h0 = 0;
        long long cur_a = a;
        long long r = 1;
        for(int i = 0; i < k-1; ++i) {
            cost_less_k_h0 += (long long)(bits(cur_a)+1) * (bits(cur_a)+1);
            if ((d_h0 >> i) & 1) {
                cost_less_k_h0 += (long long)(bits(r)+1) * (bits(cur_a)+1);
                r = (int128)r * cur_a % n;
            }
            cur_a = (int128)cur_a * cur_a % n;
        }
        cost_less_k_h0 += (long long)(bits(cur_a)+1)*(bits(cur_a)+1); // for i=k-1, d_{k-1}=0
        long long r_k_h0 = r;
        long long t_h0 = cost_less_k_h0 + 4LL * (60 - k) + 2LL * (bits(r_k_h0) + 1) * s_k_h0;

        // H1: d_{k-1}=1
        unsigned long long d_h1 = d | (1ULL << (k - 1));
        long long s_k_h1 = s[k-1] - 1;
        long long cost_less_k_h1 = 0;
        cur_a = a;
        r = 1;
        for(int i = 0; i < k-1; ++i) {
            cost_less_k_h1 += (long long)(bits(cur_a)+1) * (bits(cur_a)+1);
            if ((d_h1 >> i) & 1) {
                cost_less_k_h1 += (long long)(bits(r)+1) * (bits(cur_a)+1);
                r = (int128)r * cur_a % n;
            }
            cur_a = (int128)cur_a * cur_a % n;
        }
        cost_less_k_h1 += (long long)(bits(cur_a)+1)*(bits(cur_a)+1) + (long long)(bits(r)+1)*(bits(cur_a)+1);
        r = (int128)r * cur_a % n;
        long long r_k_h1 = r;
        long long t_h1 = cost_less_k_h1 + 4LL * (60 - k) + 2LL * (bits(r_k_h1) + 1) * s_k_h1;
        
        if (std::abs(t_obs_k - t_h0) < std::abs(t_obs_k - t_h1)) {
            s[k] = s[k-1];
        } else {
            d |= (1ULL << (k - 1));
            s[k] = s[k-1] - 1;
        }
    }
    
    long long popcnt_rem = s[S];

    for(int i=0; i<300; ++i) avg_bits_p1 += bits(rng() % n) + 1;
    avg_bits_p1 /= 300;
    if (avg_bits_p1 < 1) avg_bits_p1 = 1;


    for (int k = S; k < 60; ++k) {
        if (popcnt_rem == 0) break;
        int votes0 = 0, votes1 = 0;
        int M = 21;
        for(int j=0; j<M; ++j) {
            long long a_rand = rng() % (n - 2) + 2;
            long long t_obs_rand = query(a_rand);
            
            double t0 = predict_time(a_rand, d, k + 1, popcnt_rem);
            double t1 = predict_time(a_rand, d | (1ULL << k), k + 1, popcnt_rem - 1);

            if(std::abs(t_obs_rand - t0) < std::abs(t_obs_rand - t1)) {
                votes0++;
            } else {
                votes1++;
            }
        }
        if (votes1 > votes0) {
            d |= (1ULL << k);
            popcnt_rem--;
        }
    }

    std::cout << "! " << d << std::endl;

    return 0;
}