#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <deque>
#include <cmath>
#include <cstdlib>
#include <ctime>

// Miller-Rabin primality test
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

bool check_composite(long long n, long long a, long long d, int s) {
    long long x = power(a, d, n);
    if (x == 1 || x == n - 1)
        return false;
    for (int r = 1; r < s; r++) {
        x = (__int128)x * x % n;
        if (x == n - 1)
            return false;
    }
    return true;
}

bool is_prime(long long n) {
    if (n < 2) return false;
    int s = 0;
    long long d = n - 1;
    while ((d & 1) == 0) {
        d >>= 1;
        s++;
    }
    // Bases proven to work for all 64-bit integers
    for (long long a : {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37}) {
        if (n == a) return true;
        if (check_composite(n, a, d, s)) return false;
    }
    return true;
}

// Pollard's rho algorithm
long long pollard(long long n) {
    if (n % 2 == 0) return 2;
    if (is_prime(n)) return n;
    
    auto f = [&](long long x, long long c) {
        return ((__int128)x * x + c) % n;
    };

    long long x = 2, y = 2, d = 1;
    long long c = 1;
    while (true) {
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

void factorize(long long n, std::vector<long long>& factors) {
    if (n <= 1) return;
    if (is_prime(n)) {
        factors.push_back(n);
        return;
    }
    long long f = pollard(n);
    factorize(f, factors);
    factorize(n / f, factors);
}

std::vector<long long> get_prime_factors(long long k) {
    std::vector<long long> factors;
    for (long long i = 2; i * i <= k && i <= 1000000; ++i) {
        while (k % i == 0) {
            factors.push_back(i);
            k /= i;
        }
    }
    if (k > 1) {
        factorize(k, factors);
    }
    return factors;
}

std::deque<int> build_perm_for_k(long long k) {
    std::vector<int> ops;
    long long temp_k = k;
    while (temp_k > 1) {
        if (temp_k % 2 == 0) {
            ops.push_back(2); // op for *2
            temp_k /= 2;
        } else {
            ops.push_back(1); // op for +1
            temp_k -= 1;
        }
    }
    std::reverse(ops.begin(), ops.end());

    std::deque<int> p;
    int v = 0;
    for (int op : ops) {
        if (op == 2) { // *2
            p.push_back(v++);
        } else { // +1
            p.push_front(v++);
        }
    }
    return p;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    srand(time(0));
    int q;
    std::cin >> q;
    while (q--) {
        long long k;
        std::cin >> k;

        std::vector<long long> factors = get_prime_factors(k);
        std::vector<int> p;
        int current_val = 0;

        for (long long factor : factors) {
            std::deque<int> p_factor = build_perm_for_k(factor);
            for (int val : p_factor) {
                p.push_back(val + current_val);
            }
            current_val += p_factor.size();
        }

        std::cout << p.size() << "\n";
        for (int i = 0; i < p.size(); ++i) {
            std::cout << p[i] << (i == p.size() - 1 ? "" : " ");
        }
        std::cout << "\n";
    }

    return 0;
}