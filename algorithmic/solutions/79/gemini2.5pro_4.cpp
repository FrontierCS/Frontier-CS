#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <random>
#include <algorithm>
#include <chrono>
#include <string>

using int128 = __int128_t;

long long n;

long long bits(long long x) {
    if (x == 0) return 0;
    return 64 - __builtin_clzll(x);
}

long long query(long long a) {
    std::cout << "? " << a << std::endl;
    long long time;
    std::cin >> time;
    return time;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> n;

    std::vector<long long> d_bits(60);
    d_bits[0] = 1;

    std::mt19937_64 rng(std::chrono::steady_clock::now().time_since_epoch().count());

    double mu_b_plus_1 = 0;
    int est_samples_outer = 50;
    for(int i = 0; i < est_samples_outer; ++i) {
        mu_b_plus_1 += bits( ( (int128)rng() * rng() ) % n ) + 1;
    }
    mu_b_plus_1 /= est_samples_outer;

    double avg_term_est = mu_b_plus_1 * mu_b_plus_1;

    for (int k = 1; k < 60; ++k) {
        int votes1 = 0;
        int total_queries_left = 30000 - 1 - (k - 1) * (28000 / 59);
        int queries_for_k = total_queries_left / (60 - k);
        if (queries_for_k < 5) queries_for_k = 5;
        if (queries_for_k > 470) queries_for_k = 470;
        
        for (int s = 0; s < queries_for_k; ++s) {
            long long cur_a = rng() % (n - 2) + 2;
            long long T_obs = query(cur_a);

            std::vector<long long> a_seq(60);
            std::vector<long long> r_seq(k + 1);

            long long temp_a = cur_a;
            long long C_a = 0;
            for (int i = 0; i < 60; ++i) {
                a_seq[i] = temp_a;
                C_a += (bits(temp_a) + 1) * (bits(temp_a) + 1);
                temp_a = (int128)temp_a * temp_a % n;
            }

            r_seq[0] = 1;
            long long T_known = 0;
            for (int i = 0; i < k; ++i) {
                if (d_bits[i]) {
                    T_known += (bits(r_seq[i]) + 1) * (bits(a_seq[i]) + 1);
                    r_seq[i+1] = (int128)r_seq[i] * a_seq[i] % n;
                } else {
                    r_seq[i+1] = r_seq[i];
                }
            }
            long long Y_k = T_obs - C_a - T_known;
            long long T_k = (bits(r_seq[k]) + 1) * (bits(a_seq[k]) + 1);
            
            double noise_estim = 0.5 * (59 - k) * avg_term_est;
            
            if (Y_k > T_k / 2.0 + noise_estim) {
                 votes1++;
            }
        }
        if (votes1 > queries_for_k / 2) {
            d_bits[k] = 1;
        } else {
            d_bits[k] = 0;
        }
    }

    int128 d = 0;
    for (int i = 59; i >= 0; --i) {
        d = d * 2 + d_bits[i];
    }
    
    std::string d_str;
    if (d == 0) {
        d_str = "0";
    } else {
        int128 temp_d = d;
        while (temp_d > 0) {
            d_str += (temp_d % 10) + '0';
            temp_d /= 10;
        }
        std::reverse(d_str.begin(), d_str.end());
    }
    
    std::cout << "! " << d_str << std::endl;

    return 0;
}