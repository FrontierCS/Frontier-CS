#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>

// GF(2^k) arithmetic
int k;
int gf_mod;
std::vector<int> gf_log;
std::vector<int> gf_exp;

void gf_init(int power, int mod) {
    k = power;
    gf_mod = mod;
    int gf_size = 1 << k;
    gf_log.assign(gf_size, 0);
    gf_exp.assign(2 * gf_size, 0);

    int x = 1;
    for (int i = 0; i < gf_size - 1; ++i) {
        gf_exp[i] = x;
        gf_log[x] = i;
        x <<= 1;
        if (x >= gf_size) {
            x ^= gf_mod;
        }
    }
    for (int i = gf_size - 1; i < 2 * gf_size; ++i) {
        gf_exp[i] = gf_exp[i - (gf_size - 1)];
    }
}

int gf_mul(int a, int b) {
    if (a == 0 || b == 0) return 0;
    return gf_exp[gf_log[a] + gf_log[b]];
}

int gf_pow(int a, int p) {
    if (a == 0) return 0;
    if (p == 0) return 1;
    if (p == 1) return a;
    if (p == 2) return gf_mul(a, a);
    if (p == 3) return gf_mul(gf_mul(a, a), a);

    long long log_a = gf_log[a];
    long long log_res = (log_a * p) % ((1 << k) - 1);
    return gf_exp[log_res];
}

// Primitive polynomials for GF(2^k). The value is for x^k = p(x), so mod is p(x).
const int PRIMITIVE_POLY[] = {
    0, 0, 3, 3, 3, 5, 3, 9, 29, 9, 5, 9, 45, 39, 9, 25, 29, 9, 101, 9, 29
};

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    int n;
    std::cin >> n;

    if (n <= 8) {
        if (n == 1) {
            std::cout << "1\n1\n";
        } else if (n <= 4) {
            std::cout << "2\n1 2\n";
        } else { // 5 to 8
            std::cout << "3\n1 2 4\n";
        }
        return 0;
    }

    int m = static_cast<int>(floor(sqrt(static_cast<double>(n) / 2.0)));
    if (m == 0) m = 1;

    int k_val = 0;
    while ((1 << k_val) <= m) {
        k_val++;
    }

    gf_init(k_val, PRIMITIVE_POLY[k_val]);

    std::vector<int> S;
    S.reserve(m);
    for (int i = 1; i <= m; ++i) {
        S.push_back((i << k_val) ^ gf_pow(i, 3));
    }

    std::cout << S.size() << "\n";
    for (size_t i = 0; i < S.size(); ++i) {
        std::cout << S[i] << (i == S.size() - 1 ? "" : " ");
    }
    std::cout << "\n";

    return 0;
}