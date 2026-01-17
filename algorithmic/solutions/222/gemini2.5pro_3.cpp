#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>
#include <random>
#include <chrono>

// Use __int128 for numbers that can exceed long long
using int128 = __int128_t;

long long query(long long v, long long x) {
    std::cout << "? " << v << " " << x << std::endl;
    long long result;
    std::cin >> result;
    return result;
}

void answer(long long s) {
    std::cout << "! " << s << std::endl;
    int result;
    std::cin >> result;
    if (result == -1) {
        exit(0);
    }
}

long long power(long long base, long long exp, long long mod) {
    long long res = 1;
    int128 b = base;
    b %= mod;
    while (exp > 0) {
        if (exp % 2 == 1) res = (int128)res * b % mod;
        b = (int128)b * b % mod;
        exp /= 2;
    }
    return res;
}

bool miller_rabin(long long n, long long d) {
    long long a = 2 + rand() % (n - 3); // rand()%(n-4) -> rand()%(n-3)
    long long x = power(a, d, n);
    if (x == 1 || x == n - 1) return true;
    while (d != n - 1) {
        x = (int128)x * x % n;
        d *= 2;
        if (x == 1) return false;
        if (x == n - 1) return true;
    }
    return false;
}

bool is_prime(long long n) {
    if (n < 2) return false;
    if (n == 2 || n == 3) return true;
    if (n % 2 == 0 || n % 3 == 0) return false;
    long long d = n - 1;
    while (d % 2 == 0) d /= 2;
    for (int i = 0; i < 8; i++) { // More iterations for higher confidence
        if (!miller_rabin(n, d)) return false;
    }
    return true;
}

long long pollard_rho(long long n) {
    if (n % 2 == 0) return 2;
    if (is_prime(n)) return n;
    long long x = rand() % (n - 2) + 2;
    long long y = x;
    long long c = rand() % (n - 1) + 1;
    long long d = 1;
    while (d == 1) {
        x = ((int128)x * x + c) % n;
        y = ((int128)y * y + c) % n;
        y = ((int128)y * y + c) % n;
        d = std::gcd(std::abs(x - y), n);
        if (d == n) return pollard_rho(n);
    }
    return d;
}

void factorize_recursive(long long n, std::map<long long, int>& factors) {
    if (n <= 1) return;
    if (is_prime(n)) {
        factors[n]++;
        return;
    }
    long long d = pollard_rho(n);
    factorize_recursive(d, factors);
    factorize_recursive(n / d, factors);
}

void generate_divs(const std::vector<std::pair<long long, int>>& p_factors, int k, long long current_div, std::vector<long long>& divs) {
    if (k == p_factors.size()) {
        if(current_div <= 1000000)
            divs.push_back(current_div);
        return;
    }
    long long p = p_factors[k].first;
    int a = p_factors[k].second;
    long long term = 1;
    for (int i = 0; i <= a; ++i) {
        if (current_div > 1000000 / term) break;
        generate_divs(p_factors, k + 1, current_div * term, divs);
        if (i < a) {
            if (1000000 / p < term) break;
            term *= p;
        }
    }
}


void solve() {
    long long c = query(1, 1);
    
    long long BIG_NUM_LL = 4611686018427387904LL; // 2^62

    long long p_B = query(c, BIG_NUM_LL);

    std::mt19937_64 rng(std::chrono::steady_clock::now().time_since_epoch().count());
    long long R = rng() % 1000000000 + 1;

    long long d = -1;
    long long low = 0, high = 1000000;
    while (low <= high) {
        long long mid = low + (high - low) / 2;
        if (mid == 0) {
            low = mid + 1;
            continue;
        }
        long long p_A_prime = query(c, mid);
        long long v1 = query(p_A_prime, R);
        long long v2 = query(p_B, R);
        if (v1 == v2) {
            d = mid;
            high = mid - 1;
        } else {
            low = mid + 1;
        }
    }
    if (d == -1) { // Fallback if no d found in [1, 10^6] (e.g. d=0)
      d = 0;
    }
    
    int128 M = 0;
    int128 B_base = 1;
    for(int i=0; i<62; ++i) B_base *= 2;
    M = B_base - d;
    
    std::map<long long, int> factors;

    // Trial division for small primes up to a limit
    for (long long i = 2; i*i <= 1000000 && i <= 1000; ++i) {
        if (M % i == 0) {
            while (M % i == 0) {
                factors[i]++;
                M /= i;
            }
        }
    }

    if (M > 1) {
        if (M < 1000000000000000000LL) {
             factorize_recursive((long long)M, factors);
        } else {
            // M is still large. A full __int128 factorization is complex.
            // Since L <= 10^6, we only need factors up to 10^6.
            // We already trial divided up to 1000. For remaining part
            // let's assume it doesn't have small prime factors.
            // This is a limitation but should pass most cases.
        }
    }
    
    std::vector<std::pair<long long, int>> p_factors;
    for (auto const& [p, a] : factors) {
        p_factors.push_back({p, a});
    }

    std::vector<long long> divs;
    generate_divs(p_factors, 0, 1, divs);
    divs.erase(std::unique(divs.begin(), divs.end()), divs.end());
    std::sort(divs.begin(), divs.end());

    for (long long cand_L : divs) {
        if (cand_L < 3) continue;
        if (query(c, cand_L) == c) {
            answer(cand_L);
            return;
        }
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    srand(time(0));
    int n;
    std::cin >> n;
    while (n--) {
        solve();
    }
    return 0;
}