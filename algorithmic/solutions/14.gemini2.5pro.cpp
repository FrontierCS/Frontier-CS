#include <iostream>
#include <vector>
#include <string>
#include <map>
#include <numeric>
#include <algorithm>
#include <cmath>

long long query(const std::string& type, long long val) {
    std::cout << type << " " << val << std::endl;
    if (type == "guess") {
        return 0;
    }
    long long result;
    std::cin >> result;
    return result;
}

std::vector<long long> prime_factorize(long long n) {
    std::vector<long long> factors;
    for (long long i = 2; i * i <= n; ++i) {
        if (n % i == 0) {
            factors.push_back(i);
            while (n % i == 0) {
                n /= i;
            }
        }
    }
    if (n > 1) {
        factors.push_back(n);
    }
    return factors;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    const int B = 31622;
    std::map<long long, int> baby_steps;
    long long D = -1;

    long long current_v = query("walk", 0);

    // Phase 1: Baby-step giant-step
    baby_steps[current_v] = 0;
    for (int j = 1; j < B; ++j) {
        current_v = query("walk", 1);
        if (baby_steps.count(current_v)) {
            D = j - baby_steps[current_v];
            goto phase2;
        }
        baby_steps[current_v] = j;
    }

    current_v = query("walk", 1);
    if (baby_steps.count(current_v)) {
        D = B - baby_steps[current_v];
        goto phase2;
    }

    for (int i = 2; i <= B; ++i) {
        current_v = query("walk", B);
        if (baby_steps.count(current_v)) {
            D = (long long)i * B - baby_steps[current_v];
            goto phase2;
        }
    }

phase2:
    long long L_curr = query("walk", 0);
    
    long long n_cand = D;
    std::vector<long long> p_factors = prime_factorize(D);

    for (long long p : p_factors) {
        while (n_cand % p == 0) {
            long long g = n_cand / p;
            long long L_new = query("walk", g);
            if (L_new == L_curr) {
                n_cand = g;
            } else {
                query("walk", D - g);
                break;
            }
        }
    }

    query("guess", n_cand);

    return 0;
}