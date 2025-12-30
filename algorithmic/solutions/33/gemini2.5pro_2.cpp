#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>
#include <cmath>
#include <cstdlib>
#include <ctime>

// Using __int128 for modular multiplication to avoid overflow
long long power(long long base, long long exp, long long mod) {
    long long res = 1;
    base %= mod;
    while (exp > 0) {
        if (exp % 2 == 1) res = (__int128)res * base % mod;
        base = (__int128)base * base % mod;
        exp /= 2;
    }
    return res;
}

// Miller-Rabin primality test for 64-bit integers
bool is_prime(long long n) {
    if (n < 2) return false;
    if (n == 2 || n == 3) return true;
    if (n % 2 == 0 || n % 3 == 0) return false;
    long long d = n - 1;
    int s = 0;
    while ((d & 1) == 0) {
        d >>= 1;
        s++;
    }
    long long bases[] = {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37};
    for (long long a : bases) {
        if (n == a) return true;
        long long x = power(a, d, n);
        if (x == 1 || x == n - 1) continue;
        bool composite = true;
        for (int r = 1; r < s; ++r) {
            x = (__int128)x * x % n;
            if (x == n - 1) {
                composite = false;
                break;
            }
        }
        if (composite) return false;
    }
    return true;
}

// Pollard's rho algorithm for integer factorization
long long pollard_rho(long long n) {
    if (n % 2 == 0) return 2;
    
    auto f = [&](long long x, long long c) {
        return ((__int128)x * x + c) % n;
    };
    
    long long x = 2, y = 2, d = 1;
    long long c = 1;
    while(true){
        x = 2, y = 2, d = 1;
        while (d == 1) {
            x = f(x, c);
            y = f(f(y, c), c);
            d = std::gcd(std::abs(x - y), n);
        }
        if (d != n) return d;
        c++;
    }
}

void factorize(long long n, std::map<long long, int>& factors) {
    if (n <= 1) return;
    
    while (n > 1) {
        if (is_prime(n)) {
            factors[n]++;
            break;
        }
        long long factor = pollard_rho(n);
        factorize(factor, factors);
        n /= factor;
    }
}

void solve() {
    long long k;
    std::cin >> k;

    std::map<long long, int> prime_factors;
    long long temp_k = k;
    for (long long i = 2; i * i <= temp_k && i <= 1000000; ++i) {
        while (temp_k % i == 0) {
            prime_factors[i]++;
            temp_k /= i;
        }
    }
    if (temp_k > 1) {
        factorize(temp_k, prime_factors);
    }
    
    std::vector<std::pair<long long, int>> factors_for_blocks;
    if (prime_factors.count(2)) {
        factors_for_blocks.push_back({2, prime_factors[2]});
        prime_factors.erase(2);
    }
    for (auto const& [p, count] : prime_factors) {
        for (int i = 0; i < count; ++i) {
            factors_for_blocks.push_back({p, 1});
        }
    }
    std::sort(factors_for_blocks.begin(), factors_for_blocks.end());

    std::vector<int> p_result;
    int current_val = 0;

    for (auto const& [factor_val, count] : factors_for_blocks) {
        if (factor_val == 2) {
            // increasing block of length 'count' for factor 2^count
            int m = count;
            for (int i = 0; i < m; ++i) {
                p_result.push_back(current_val + i);
            }
            current_val += m;
        } else {
            // decreasing block of length factor_val - 1 for factor p
            int c = factor_val - 1;
            for (int i = 0; i < c; ++i) {
                p_result.push_back(current_val + c - 1 - i);
            }
            current_val += c;
        }
    }

    std::cout << p_result.size() << "\n";
    for (int i = 0; i < p_result.size(); ++i) {
        std::cout << p_result[i] << (i == p_result.size() - 1 ? "" : " ");
    }
    std::cout << "\n";
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    srand(time(0));
    int q;
    std::cin >> q;
    while (q--) {
        solve();
    }
    return 0;
}