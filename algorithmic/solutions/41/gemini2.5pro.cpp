#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <map>

// Using __int128 for objective value to avoid overflow
using int128 = __int128;

long long n;
std::vector<int> primes;
const int SIEVE_LIMIT = 2000000;
std::vector<bool> is_prime;

void sieve() {
    is_prime.assign(SIEVE_LIMIT + 1, true);
    is_prime[0] = is_prime[1] = false;
    for (int p = 2; p * p <= SIEVE_LIMIT; ++p) {
        if (is_prime[p]) {
            for (int i = p * p; i <= SIEVE_LIMIT; i += p)
                is_prime[i] = false;
        }
    }
    primes.reserve(SIEVE_LIMIT / 10);
    for (int p = 2; p <= SIEVE_LIMIT; ++p) {
        if (is_prime[p]) {
            primes.push_back(p);
        }
    }
}

int128 calculate_v(const std::vector<long long>& a) {
    if (a.empty()) {
        return 0;
    }
    long long c = n / a.back();
    if (c == 0) c = 1;
    int128 sum = 0;
    for (long long val : a) {
        sum += val;
    }
    return (int128)a.size() * c * sum;
}

std::map<long long, int> prime_factorize(long long num) {
    std::map<long long, int> counts;
    long long temp = num;
    for (long long i = 2; i * i <= temp; ++i) {
        if (temp % i == 0) {
            while (temp % i == 0) {
                counts[i]++;
                temp /= i;
            }
        }
    }
    if (temp > 1) counts[temp]++;
    return counts;
}

std::vector<long long> get_divs(const std::map<long long, int>& counts) {
    std::vector<long long> divs;
    divs.push_back(1);
    
    for(auto const& [p, count] : counts) {
        int current_size = divs.size();
        long long p_power = 1;
        for (int i = 0; i < count; ++i) {
            p_power *= p;
            if ((long double)divs.back() * p_power > 2e12) break; // Heuristic bound to prevent too many divisors
            for (int j = 0; j < current_size; ++j) {
                divs.push_back(divs[j] * p_power);
            }
        }
    }
    std::sort(divs.begin(), divs.end());
    return divs;
}


int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> n;
    
    sieve();

    std::vector<long long> best_seq;
    int128 best_v = -1;

    // Base Case: sequence of length 1
    best_seq.push_back(1);
    best_v = calculate_v(best_seq);

    // Construction P: a_1 = p_1, a_i = p_i * p_{i-1}
    std::vector<long long> seq_p;
    if (primes.size() > 0) {
        seq_p.push_back(primes[0]);
        for (size_t i = 1; i < primes.size(); ++i) {
            long double p_i = primes[i];
            long double p_im1 = primes[i-1];
            if (p_i * p_im1 > n) {
                break;
            }
            seq_p.push_back((long long)primes[i] * primes[i-1]);
        }
    }

    if (!seq_p.empty()) {
        int128 current_v = calculate_v(seq_p);
        if (current_v > best_v) {
            best_v = current_v;
            best_seq = seq_p;
        }
    }
    
    // One step extension
    if (seq_p.size() >= 2) {
        std::vector<long long> seq_p_ext = seq_p;
        long long p_k = primes[seq_p.size()-1];
        long long p_km1 = primes[seq_p.size()-2];
        
        long long next_a;
        if ((long double)p_k * (p_km1 + 1) <= n) {
            next_a = p_k * (p_km1 + 1);
            seq_p_ext.push_back(next_a);
            int128 current_v = calculate_v(seq_p_ext);
            if (current_v > best_v) {
                best_v = current_v;
                best_seq = seq_p_ext;
            }

            // Two step extension
            if (seq_p_ext.size() >= 2) {
                long long ak = seq_p_ext.back();
                long long akm1 = seq_p_ext[seq_p_ext.size()-2];
                long long gk = std::gcd(ak, akm1);

                auto counts = prime_factorize(ak);
                auto divs = get_divs(counts);
                
                for (long long d : divs) {
                    if (d > gk) {
                        if (ak <= n - d) {
                            long long next_a2 = ak + d;
                            std::vector<long long> seq_p_ext2 = seq_p_ext;
                            seq_p_ext2.push_back(next_a2);
                            int128 v2 = calculate_v(seq_p_ext2);
                            if (v2 > best_v) {
                               best_v = v2;
                               best_seq = seq_p_ext2;
                            }
                        }
                        break; 
                    }
                }
            }
        }
    }

    // A simple sequence 1, 2, 4, 8...
    std::vector<long long> seq_pow2;
    seq_pow2.push_back(1);
    long long current = 1;
    while(true) {
        if (current > n / 2) break;
        current *= 2;
        seq_pow2.push_back(current);
    }
     if (!seq_pow2.empty()) {
        int128 current_v = calculate_v(seq_pow2);
        if (current_v > best_v) {
            best_v = current_v;
            best_seq = seq_pow2;
        }
    }
    
    std::cout << best_seq.size() << "\n";
    long long c = n / best_seq.back();
    if (c == 0) c = 1;
    for (size_t i = 0; i < best_seq.size(); ++i) {
        std::cout << best_seq[i] * c << (i == best_seq.size() - 1 ? "" : " ");
    }
    std::cout << "\n";

    return 0;
}