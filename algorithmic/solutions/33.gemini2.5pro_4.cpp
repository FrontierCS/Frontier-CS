#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>
#include <cmath>
#include <ctime>

// Using __int128 for safe multiplication in Miller-Rabin and Pollard's rho
long long power_mod(long long base, long long exp, long long mod) {
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
    long long x = power_mod(a, d, n);
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
    auto f = [&](long long val) {
        return ((__int128)val * val + c) % n;
    };
    while (d == 1) {
        x = f(x);
        y = f(f(y));
        d = std::gcd(std::abs(x - y), n);
        if (d == n) {
            y = rand() % (n - 2) + 2;
            x = y;
            c = rand() % (n - 1) + 1;
            d = 1;
        }
    }
    return d;
}

void factorize(long long n, std::map<long long, int>& factors) {
    if (n <= 1) return;
    if (is_prime(n)) {
        factors[n]++;
        return;
    }
    long long d = pollard(n);
    factorize(d, factors);
    factorize(n / d, factors);
}

long long get_cost(long long f) {
    if (f <= 1) return 0;
    long long cost = f - 1;
    if ((f > 0) && ((f & (f - 1)) == 0)) {
        cost = std::min(cost, (long long)__builtin_ctzll(f));
    }
    if (f > 1) {
        long long fm1 = f - 1;
        if ((fm1 > 0) && ((fm1 & (fm1 - 1)) == 0)) {
            cost = std::min(cost, (long long)__builtin_ctzll(fm1) + 1);
        }
    }
    return cost;
}

std::map<std::pair<long long, int>, std::vector<long long>> memo_factors;

void solve_for_p_power(long long p, int a, std::vector<long long>& factors_list) {
    if (memo_factors.count({p, a})) {
        for (long long f : memo_factors[{p, a}]) {
            factors_list.push_back(f);
        }
        return;
    }

    std::vector<std::pair<long long, int>> dp(a + 1);
    dp[0] = {0, 0};
    for (int i = 1; i <= a; ++i) {
        dp[i] = {-1, -1};
        long long p_power = 1;
        for (int j = 1; j <= i; ++j) {
            if (p > std::numeric_limits<long long>::max() / p_power) {
                 p_power = std::numeric_limits<long long>::max();
            } else {
                 p_power *= p;
            }
            long long current_cost = get_cost(p_power);
            if (dp[i].first == -1 || dp[i-j].first + current_cost < dp[i].first) {
                dp[i] = {dp[i-j].first + current_cost, j};
            }
        }
    }

    std::vector<long long> p_factors;
    int current_a = a;
    while (current_a > 0) {
        int j = dp[current_a].second;
        long long factor = 1;
        for (int l = 0; l < j; ++l) factor *= p;
        p_factors.push_back(factor);
        current_a -= j;
    }
    memo_factors[{p, a}] = p_factors;
    for (long long f : p_factors) {
        factors_list.push_back(f);
    }
}

void solve_query() {
    long long k;
    std::cin >> k;

    std::map<long long, int> prime_factors;
    factorize(k, prime_factors);

    std::vector<long long> factors_list;
    for (auto const& [p, a] : prime_factors) {
        solve_for_p_power(p, a, factors_list);
    }
    
    std::vector<int> p_perm;
    int current_val = 0;
    for (long long f : factors_list) {
        long long len = 0;
        int type = -1;
        long long cost = -1;
        
        cost = f - 1;
        len = f - 1;
        type = 0;

        if ((f > 0) && ((f & (f - 1)) == 0)) {
            long long ctz = __builtin_ctzll(f);
            if (ctz < cost) {
                cost = ctz;
                len = ctz;
                type = 1;
            }
        }
        
        if (f > 1) {
            long long fm1 = f - 1;
            if ((fm1 > 0) && ((fm1 & (fm1 - 1)) == 0)) {
                long long ctz = __builtin_ctzll(fm1);
                if (ctz + 1 < cost) {
                    cost = ctz + 1;
                    len = ctz + 1;
                    type = 2;
                }
            }
        }

        if (len == 0) continue;

        if (type == 0) {
            for (int i = 0; i < len; ++i) {
                p_perm.push_back(current_val + len - 1 - i);
            }
        } else if (type == 1) {
            for (int i = 0; i < len; ++i) {
                p_perm.push_back(current_val + i);
            }
        } else {
            for (int i = 0; i < len - 1; ++i) {
                p_perm.push_back(current_val + 1 + i);
            }
            p_perm.push_back(current_val);
        }
        current_val += len;
    }
    
    std::cout << p_perm.size() << "\n";
    for (size_t i = 0; i < p_perm.size(); ++i) {
        std::cout << p_perm[i] << (i == p_perm.size() - 1 ? "" : " ");
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
        solve_query();
    }
    return 0;
}