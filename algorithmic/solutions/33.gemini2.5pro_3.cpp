#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>
#include <cstdlib>
#include <ctime>

// Using __int128_t for modular arithmetic to avoid overflow in Pollard's rho
using int128 = __int128_t;

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

bool miller_rabin(long long n, long long d) {
    long long a = 2 + rand() % (n - 3); // n > 4
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
    for (int i = 0; i < 8; i++) { // Iterations for high confidence
        if (n < 5) break;
        if (!miller_rabin(n, d)) return false;
    }
    return true;
}

long long pollard_rho(long long n) {
    if (n % 2 == 0) return 2;
    if (is_prime(n)) return n;
    
    long long x = rand() % (n - 2) + 1;
    long long y = x;
    long long c = rand() % (n - 1) + 1;
    long long d = 1;

    while (d == 1) {
        x = ((int128)x * x + c) % n;
        y = ((int128)y * y + c) % n;
        y = ((int128)y * y + c) % n;
        long long diff = x > y ? x - y : y - x;
        d = std::gcd(diff, n);
        if (d == n) { // Retry with different parameters if cycle found
             x = rand() % (n - 2) + 1;
             y = x;
             c = rand() % (n - 1) + 1;
        }
    }
    return d;
}

void factorize(long long k, std::map<long long, int>& factors) {
    if (k <= 1) return;
    if (is_prime(k)) {
        factors[k]++;
        return;
    }
    long long d = pollard_rho(k);
    factorize(d, factors);
    factorize(k / d, factors);
}

std::vector<int> generate_perm(long long k) {
    if (k <= 1) {
        return {};
    }

    std::vector<int> ops;
    long long temp_k = k;
    while (temp_k > 1) {
        if (temp_k % 2 == 0) {
            ops.push_back(2); // Op*2
            temp_k /= 2;
        } else {
            ops.push_back(1); // Op+1
            temp_k -= 1;
        }
    }
    std::reverse(ops.begin(), ops.end());

    std::vector<int> p;
    for (int op : ops) {
        if (op == 1) { // k -> k+1, prepend new max
            p.insert(p.begin(), p.size());
        } else { // k -> 2k, shift and prepend 0
            for (int& val : p) {
                val++;
            }
            p.insert(p.begin(), 0);
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
    std::vector<long long> ks(q);
    for (int i = 0; i < q; ++i) {
        std::cin >> ks[i];
    }

    for (long long k : ks) {
        std::map<long long, int> factors;
        long long temp_k = k;
        
        for (long long i = 2; i * i <= temp_k && i <= 1000000; ++i) {
            while (temp_k % i == 0) {
                factors[i]++;
                temp_k /= i;
            }
        }
        if (temp_k > 1) {
            factorize(temp_k, factors);
        }

        std::vector<int> final_perm;
        int current_offset = 0;

        for (auto const& [p_val, count] : factors) {
            std::vector<int> p_perm = generate_perm(p_val);
            for (int i = 0; i < count; ++i) {
                for (int val : p_perm) {
                    final_perm.push_back(val + current_offset);
                }
                current_offset += p_perm.size();
            }
        }

        std::cout << final_perm.size() << "\n";
        for (int i = 0; i < final_perm.size(); ++i) {
            std::cout << final_perm[i] << (i == final_perm.size() - 1 ? "" : " ");
        }
        std::cout << "\n";
    }

    return 0;
}