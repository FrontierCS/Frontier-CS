#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <iomanip>

struct Point {
    double x, y, z;
};

// Simple Cubic grid parameters
int sc_m, sc_k, sc_l;
double r_sc;

// Face-Centered Cubic lattice parameters
int fcc_m;
double r_fcc;

long long num_fcc_points(int m) {
    if (m <= 0) return 0;
    long long m_ll = m;
    if (m % 2 == 0) {
        return m_ll * m_ll * m_ll / 2;
    } else {
        return (m_ll * m_ll * m_ll + 1) / 2;
    }
}

void solve_sc(int n) {
    long long n_ll = n;
    int best_D = n;
    sc_m = n;
    sc_k = 1;
    sc_l = 1;

    int limit_m = cbrt(2.0 * n) + 2;
    if (limit_m > n) limit_m = n;

    for (int m = 1; m <= limit_m; ++m) {
        int limit_k = sqrt(2.0 * n / m) + 2;
        if (limit_k > n) limit_k = n;
        for (int k = m; k <= limit_k; ++k) {
            if ((long long)m * k > 2 * n_ll && n > 1) continue;
            int l = (n_ll + (long long)m * k - 1) / ((long long)m * k);
            
            int D = std::max({m, k, l});
            if (D < best_D) {
                best_D = D;
                sc_m = m;
                sc_k = k;
                sc_l = l;
            }
        }
    }
    
    int limit_m2d = sqrt(2.0 * n) + 2;
    if (limit_m2d > n) limit_m2d = n;
    for (int m = 1; m <= limit_m2d; ++m) {
        int k = (n + m - 1) / m;
        int l = 1;
        int D = std::max({m,k,l});
        if ((long long)m*k*l >= n_ll && D < best_D) {
            best_D = D;
            sc_m = m; sc_k = k; sc_l = l;
        }
    }


    r_sc = 0.5 / best_D;
}


void solve_fcc(int n) {
    if (n == 0) {
        r_fcc = 0;
        return;
    }
    fcc_m = 0;
    while(num_fcc_points(fcc_m) < n) {
        fcc_m++;
    }
    
    if (fcc_m <= 1) {
        r_fcc = 0.0;
        return;
    }
    
    r_fcc = 1.0 / ( (fcc_m - 1.0) * sqrt(2.0) + 2.0 );
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    solve_sc(n);
    solve_fcc(n);

    std::cout << std::fixed << std::setprecision(17);

    if (r_sc >= r_fcc) {
        std::vector<Point> centers;
        centers.reserve(n);
        for (int i = 0; i < sc_m; ++i) {
            for (int j = 0; j < sc_k; ++j) {
                for (int p = 0; p < sc_l; ++p) {
                    if (centers.size() < n) {
                        centers.push_back({(i + 0.5) / sc_m, (j + 0.5) / sc_k, (p + 0.5) / sc_l});
                    } else {
                        goto end_sc;
                    }
                }
            }
        }
        end_sc:;
        for (const auto& p : centers) {
            std::cout << p.x << " " << p.y << " " << p.z << "\n";
        }
    } else {
        double A = 1.0 / (fcc_m - 1.0 + sqrt(2.0));
        double offset = A / sqrt(2.0);

        int count = 0;
        for (int i = 0; i < fcc_m; ++i) {
            for (int j = 0; j < fcc_m; ++j) {
                for (int k = 0; k < fcc_m; ++k) {
                    if ((i + j + k) % 2 == 0) {
                        if (count < n) {
                            std::cout << A * i + offset << " " << A * j + offset << " " << A * k + offset << "\n";
                            count++;
                        } else {
                            goto end_fcc;
                        }
                    }
                }
            }
        }
        end_fcc:;
    }

    return 0;
}