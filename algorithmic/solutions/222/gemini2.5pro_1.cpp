#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>
#include <cmath>
#include <cstdlib>
#include <ctime>

// Using __int128 for intermediate products to prevent overflow.
using int128 = __int128;

long long power(long long base, long long exp, long long mod) {
    long long res = 1;
    base %= mod;
    while (exp > 0) {
        if (exp % 2 == 1) res = (int128)res * base % mod;
        base = (int128)base * base % mod;
        exp /= 2;
    }
    return res;
}

bool check_composite(long long n, long long a, long long d, int s) {
    long long x = power(a, d, n);
    if (x == 1 || x == n - 1)
        return false;
    for (int r = 1; r < s; r++) {
        x = (int128)x * x % n;
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
    for (long long a : {2, 3, 5, 7, 11, 13, 17, 19, 23, 29, 31, 37}) {
        if (n == a) return true;
        if (check_composite(n, a, d, s)) return false;
    }
    return true;
}

long long pollard(long long n) {
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
        if (d == n) return pollard(n);
    }
    return d;
}

void factorize(long long n, std::map<long long, int>& factors) {
    if (n <= 1) return;
    if (is_prime(n)) {
        factors[n]++;
        return;
    }
    long long f = pollard(n);
    factorize(f, factors);
    factorize(n / f, factors);
}

long long ask_query(int v, long long x) {
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

void get_divisors_recursive(long long current_divisor, int factor_idx, const std::vector<std::pair<long long, int>>& prime_factors, std::vector<long long>& divisors) {
    if (factor_idx == (int)prime_factors.size()) {
        divisors.push_back(current_divisor);
        return;
    }
    long long p = prime_factors[factor_idx].first;
    int a = prime_factors[factor_idx].second;
    long long p_power = 1;
    for (int i = 0; i <= a; ++i) {
        get_divisors_recursive(current_divisor * p_power, factor_idx + 1, prime_factors, divisors);
        p_power *= p;
    }
}

std::vector<long long> get_all_divisors(long long n) {
    if (n == 0) return {};
    std::map<long long, int> factors;
    factorize(n, factors);
    std::vector<std::pair<long long, int>> prime_factors(factors.begin(), factors.end());
    std::vector<long long> divisors;
    get_divisors_recursive(1, 0, prime_factors, divisors);
    std::sort(divisors.begin(), divisors.end());
    return divisors;
}

long long custom_gcd(long long a, long long b) {
    if (a == 0) return b;
    if (b == 0) return a;
    return std::gcd(a, b);
}

void solve() {
    int start_node = (rand() % 1000000) + 1;
    long long large_step = (( (long long)rand() * rand() * rand() ) % (long long)(5e18)) + 1;
    int v0 = ask_query(start_node, large_step);

    long long D = 0;
    
    for(long long base : {2, 3, 5, 7}) {
        std::map<int, int> seen;
        for (int k = 0; k < 63; ++k) {
            unsigned __int128 p = 1;
            bool ovf = false;
            for(int i=0; i<k; ++i) {
                if (__builtin_mul_overflow(p, base, &p)) {
                    ovf = true;
                    break;
                }
            }
            if(ovf || p > 5000000000000000000ULL) break;

            long long step = 1;
            for(int i=0; i<k; ++i) step *= base;

            int curr_v = ask_query(v0, step);
            if (seen.count(curr_v)) {
                int j = seen[curr_v];
                long long step_j = 1;
                for(int i=0; i<j; ++i) step_j *= base;

                long long diff = step - step_j;
                D = custom_gcd(D, diff);
                break;
            }
            seen[curr_v] = k;
        }
        if (D != 0 && D < (long long)1e12) break;
    }

    if (D == 0) { 
        std::map<int, long long> seen;
        for (int i = 0; i < 2000; ++i) {
            long long x = ( (long long)rand() * rand() * rand() ) % (long long)(5e18) + 1;
            int v = ask_query(v0, x);
            if(seen.count(v)) {
                D = custom_gcd(D, std::abs(x-seen[v]));
            } else {
                seen[v] = x;
            }
        }
    }


    std::vector<long long> divisors = get_all_divisors(D);

    long long low = 0, high = divisors.size() - 1;
    long long s = D;

    while (low <= high) {
        long long mid_idx = low + (high - low) / 2;
        long long d = divisors[mid_idx];
        if (d < 3) {
            low = mid_idx + 1;
            continue;
        }
        if (ask_query(v0, d) == v0) {
            s = d;
            high = mid_idx - 1;
        } else {
            low = mid_idx + 1;
        }
    }

    answer(s);
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