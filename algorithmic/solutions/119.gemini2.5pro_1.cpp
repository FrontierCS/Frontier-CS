#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <cmath>
#include <map>
#include <algorithm>

// Computes (base^exp) % mod
long long power(long long base, long long exp) {
    long long res = 1;
    long long mod = 1000000007;
    base %= mod;
    while (exp > 0) {
        if (exp % 2 == 1) res = (res * base) % mod;
        base = (base * base) % mod;
        exp /= 2;
    }
    return res;
}

// Computes modular inverse of n under mod
long long modInverse(long long n) {
    return power(n, 1000000007 - 2);
}

// Solves for x in g^x = target (mod M) where x is a bitmask of B bits
// using Baby-Step Giant-Step algorithm
long long solve_bsgs_for_mask(long long g, long long target, int B) {
    long long M = 1000000007;
    int m_exp = (B + 1) / 2;
    long long m = 1LL << m_exp;
    
    std::map<long long, long long> table;
    long long current_g_power = 1;
    for (long long r = 0; r < m; ++r) {
        if (table.find(current_g_power) == table.end()) {
            table[current_g_power] = r;
        }
        current_g_power = (current_g_power * g) % M;
    }

    long long g_inv_m = modInverse(power(g, m));
    long long current_target_mult = target;
    long long q_limit = (1LL << (B - m_exp));

    for (long long q = 0; q < q_limit; ++q) {
        if (table.count(current_target_mult)) {
            long long r = table[current_target_mult];
            return (q * m + r);
        }
        current_target_mult = (current_target_mult * g_inv_m) % M;
    }
    return 0; // Should not be reached if target is a power of g
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    std::vector<int> ops(n + 1, 0);
    const int B = 30;
    const long long g = 5;
    const long long M = 1000000007;

    std::vector<long long> g_powers_of_2_exp(B);
    g_powers_of_2_exp[0] = g;
    for (int i = 1; i < B; ++i) {
        g_powers_of_2_exp[i] = (g_powers_of_2_exp[i - 1] * g_powers_of_2_exp[i - 1]) % M;
    }

    std::vector<long long> a(n + 1);

    for (int i = 0; i * B < n; ++i) {
        int start_idx = i * B + 1;
        int end_idx = std::min((i + 1) * B, n);

        std::fill(a.begin() + 1, a.end(), 1);
        for (int k = start_idx; k <= end_idx; ++k) {
            a[k] = g_powers_of_2_exp[k - start_idx];
        }

        a[0] = 2;
        std::cout << "?";
        for (int val : a) {
            std::cout << " " << val;
        }
        std::cout << std::endl;
        long long r1;
        std::cin >> r1;

        a[0] = 3;
        std::cout << "?";
        for (int val : a) {
            std::cout << " " << val;
        }
        std::cout << std::endl;
        long long r2;
        std::cin >> r2;

        long long diff = (r2 - r1 + M) % M;
        
        int current_B = end_idx - start_idx + 1;
        long long exponent_mask = solve_bsgs_for_mask(g, diff, current_B);

        for (int j = 0; j < current_B; ++j) {
            if ((exponent_mask >> j) & 1) {
                ops[start_idx + j] = 1;
            }
        }
    }

    std::cout << "!";
    for (int i = 1; i <= n; ++i) {
        std::cout << " " << ops[i];
    }
    std::cout << std::endl;

    return 0;
}