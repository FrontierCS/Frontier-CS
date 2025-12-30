#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <map>

void fast_io() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
}

const int SIEVE_LIMIT = 20000; // p_2000 is 17389, so 20000 is safe
std::vector<int> primes;
bool is_prime[SIEVE_LIMIT + 1];

void sieve(int limit) {
    std::fill(is_prime, is_prime + limit + 1, true);
    is_prime[0] = is_prime[1] = false;
    for (int p = 2; p * p <= limit; ++p) {
        if (is_prime[p]) {
            for (int i = p * p; i <= limit; i += p)
                is_prime[i] = false;
        }
    }
    for (int p = 2; p <= limit; ++p) {
        if (is_prime[p]) {
            primes.push_back(p);
        }
    }
}

int main() {
    fast_io();

    int n;
    std::cin >> n;

    sieve(SIEVE_LIMIT);

    std::vector<int> A(n + 1), B(n + 1);
    for (int i = 1; i <= n; ++i) {
        A[i] = primes[i - 1];
        B[i] = primes[i - 1 + n];
    }

    for (int i = 1; i <= n; ++i) {
        std::string w(A[i], 'X');
        w.append(B[i], 'O');
        std::cout << w << "\n";
    }
    std::cout.flush();

    std::map<long long, std::pair<int, int>> power_to_indices;
    std::vector<long long> D(n + 1);
    for (int i = 1; i <= n; ++i) {
        D[i] = (long long)A[i] + B[i] + (long long)A[i] * B[i];
    }

    for (int u = 1; u <= n; ++u) {
        for (int v = 1; v <= n; ++v) {
            int max_idx = std::max(u, v);
            long long power = D[max_idx] + (long long)B[u] * A[v];
            power_to_indices[power] = {u, v};
        }
    }

    int q;
    std::cin >> q;
    while (q--) {
        long long p;
        std::cin >> p;
        auto indices = power_to_indices.at(p);
        std::cout << indices.first << " " << indices.second << "\n";
        std::cout.flush();
    }

    return 0;
}