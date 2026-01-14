#include <iostream>
#include <vector>
#include <numeric>
#include <random>
#include <algorithm>
#include <map>

using int128 = __int128_t;

long long query(long long v, unsigned long long x) {
    std::cout << "? " << v << " " << x << std::endl;
    long long result;
    std::cin >> result;
    return result;
}

void answer(long long s) {
    std::cout << "! " << s << std::endl;
    int response;
    std::cin >> response;
    if (response == -1) {
        exit(0);
    }
}

int128 gcd(int128 a, int128 b) {
    while (b) {
        a %= b;
        std::swap(a, b);
    }
    return a;
}

std::vector<long long> partial_prime_factors(int128 n) {
    std::vector<long long> factors;
    for (long long i = 2; i <= 1000000; ++i) {
        if (n % i == 0) {
            factors.push_back(i);
            while (n % i == 0) {
                n /= i;
            }
        }
    }
    if (n > 1 && n <= 1000000) {
        factors.push_back((long long)n);
    }
    return factors;
}

void solve() {
    long long start_node_on_cycle = query(1, 1000000000000000000ULL);

    const int K = 2000;
    std::map<long long, std::vector<unsigned long long>> responses;

    std::random_device rd;
    std::mt19937_64 gen(rd());
    std::uniform_int_distribution<unsigned long long> dis(1, 5'000'000'000'000'000'000ULL);

    for (int i = 0; i < K; ++i) {
        unsigned long long x = dis(gen);
        long long v = query(start_node_on_cycle, x);
        responses[v].push_back(x);
    }

    int128 cycle_len_multiple = 0;

    for (auto const& [v, xs] : responses) {
        if (xs.size() > 1) {
            for (size_t i = 0; i < xs.size(); ++i) {
                for (size_t j = i + 1; j < xs.size(); ++j) {
                    int128 diff;
                    if (xs[i] > xs[j]) {
                        diff = (int128)xs[i] - xs[j];
                    } else {
                        diff = (int128)xs[j] - xs[i];
                    }

                    if (cycle_len_multiple == 0) {
                        cycle_len_multiple = diff;
                    } else {
                        cycle_len_multiple = gcd(cycle_len_multiple, diff);
                    }
                }
            }
        }
    }
    
    if (cycle_len_multiple == 0) {
        // This case is extremely unlikely with K=2000 and s <= 10^6
        // Fallback for safety, though it shouldn't be hit in practice.
        // A simple BSGS would be another 2000 queries, which exceeds the total limit.
        // A minimal walk could find very small cycles.
        long long current_node = start_node_on_cycle;
        for (long long s = 1; s <= 500; ++s) {
            current_node = query(current_node, 1);
            if (current_node == start_node_on_cycle) {
                if (s >= 3) {
                    answer(s);
                    return;
                }
            }
        }
    }

    int128 s_candidate = cycle_len_multiple;
    std::vector<long long> factors = partial_prime_factors(s_candidate);

    for (long long p : factors) {
        while (s_candidate % p == 0) {
            int128 next_s = s_candidate / p;
            if (next_s < 3) {
                break;
            }
            if (query(start_node_on_cycle, (unsigned long long)next_s) == start_node_on_cycle) {
                s_candidate = next_s;
            } else {
                break;
            }
        }
    }

    answer((long long)s_candidate);
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    int n;
    std::cin >> n;
    while (n--) {
        solve();
    }
    return 0;
}