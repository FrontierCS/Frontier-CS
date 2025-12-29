#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>

const long long MOD = 1000000007;

// Function for modular exponentiation
long long power(long long base, long long exp) {
    long long res = 1;
    base %= MOD;
    while (exp > 0) {
        if (exp % 2 == 1) res = (res * base) % MOD;
        base = (base * base) % MOD;
        exp /= 2;
    }
    return res;
}

// Function to compute modular inverse
long long modInverse(long long n) {
    return power(n, MOD - 2);
}

// Helper function to issue a query
void issue_query(int n, const std::vector<long long>& a) {
    std::cout << "?";
    for (int i = 0; i <= n; ++i) {
        std::cout << " " << a[i];
    }
    std::cout << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    // Generate a list of small prime numbers
    std::vector<int> primes;
    std::vector<bool> is_prime(200, true);
    is_prime[0] = is_prime[1] = false;
    for (int p = 2; p < 200 && primes.size() < 35; ++p) {
        if (is_prime[p]) {
            primes.push_back(p);
            for (int i = p * p; i < 200; i += p)
                is_prime[i] = false;
        }
    }

    std::vector<int> ops(n + 1, 0);
    int block_size = 30;
    int known_ops = 0;

    while (known_ops < n) {
        int current_block_size = std::min(block_size, n - known_ops);
        
        std::vector<long long> a1(n + 1, 1);
        std::vector<long long> a2(n + 1, 1);
        
        a1[0] = 1;
        a2[0] = 2;

        // Assign distinct primes to the current block of operators
        for (int i = 0; i < current_block_size; ++i) {
            a1[known_ops + 1 + i] = primes[i];
            a2[known_ops + 1 + i] = primes[i];
        }

        issue_query(n, a1);
        long long v1;
        std::cin >> v1;

        issue_query(n, a2);
        long long v2;
        std::cin >> v2;

        long long A_prime = (v2 - v1 + MOD) % MOD;
        
        // Factorize A_prime to determine multiplication operators
        for (int i = 0; i < current_block_size; ++i) {
            if (A_prime % primes[i] == 0) {
                ops[known_ops + 1 + i] = 1; // Multiplication
                A_prime = (A_prime * modInverse(primes[i])) % MOD;
            } else {
                ops[known_ops + 1 + i] = 0; // Addition
            }
        }
        known_ops += current_block_size;
    }

    std::cout << "!";
    for (int i = 1; i <= n; ++i) {
        std::cout << " " << ops[i];
    }
    std::cout << std::endl;

    return 0;
}