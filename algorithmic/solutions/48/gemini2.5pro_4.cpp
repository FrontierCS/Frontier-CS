#include <iostream>
#include <vector>
#include <cmath>
#include <iomanip>
#include <algorithm>
#include <tuple>

// Generates centers for a baseline m x k x l grid packing.
void generate_baseline(int n, int m, int k, int l) {
    int count = 0;
    for (int i = 0; i < m && count < n; ++i) {
        for (int j = 0; j < k && count < n; ++j) {
            for (int p = 0; p < l && count < n; ++p) {
                double x = (static_cast<double>(i) + 0.5) / m;
                double y = (static_cast<double>(j) + 0.5) / k;
                double z = (static_cast<double>(p) + 0.5) / l;
                std::cout << x << " " << y << " " << z << "\n";
                count++;
            }
        }
    }
}

// Generates centers for a Face-Centered Cubic (FCC) lattice packing.
void generate_fcc(int n, int M) {
    double a = 1.0 / (static_cast<double>(M) - 1.0 + std::sqrt(2.0));
    double b = (1.0 - a * (static_cast<double>(M) - 1.0)) / 2.0;
    int count = 0;
    for (int i = 0; i < M && count < n; ++i) {
        for (int j = 0; j < M && count < n; ++j) {
            for (int k = 0; k < M && count < n; ++k) {
                if ((i + j + k) % 2 == 0) {
                    double x = a * i + b;
                    double y = a * j + b;
                    double z = a * k + b;
                    std::cout << x << " " << y << " " << z << "\n";
                    count++;
                }
            }
        }
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    
    int n;
    std::cin >> n;

    // Baseline grid calculation
    int best_m = -1, best_k = -1, best_l = -1;
    long long min_L = -1;

    long long m_limit = std::cbrt(n) + 2;
    for (long long m = 1; m <= m_limit; ++m) {
        long long k_limit = std::sqrt(static_cast<double>(n) / m) + 2;
        for (long long k = m; k <= k_limit; ++k) {
            if (m > 0 && k > 0 && n / m / k > n) continue; // Basic overflow check
            long long l = std::ceil(static_cast<double>(n) / (m * k));
            long long L = std::max({m, k, l});
            if (min_L == -1 || L < min_L) {
                min_L = L;
                best_m = m;
                best_k = k;
                best_l = l;
            }
        }
    }
    if (best_m == -1) { // Fallback for any missed cases
       long long s = std::ceil(std::cbrt(n));
       best_m = s; best_k = s; best_l = s;
       min_L = s;
    }
    double r_base = 1.0 / (2.0 * min_L);

    // FCC lattice calculation
    int M = 1;
    while (true) {
        long long m_ll = M;
        long long num_points = std::ceil(static_cast<double>(m_ll) * m_ll * m_ll / 2.0);
        if (num_points >= n) {
            break;
        }
        M++;
    }
    double r_fcc = std::sqrt(2.0) / (2.0 * (static_cast<double>(M) - 1.0 + std::sqrt(2.0)));
    
    std::cout << std::fixed << std::setprecision(17);

    if (r_base > r_fcc) {
        generate_baseline(n, best_m, best_k, best_l);
    } else {
        generate_fcc(n, M);
    }

    return 0;
}