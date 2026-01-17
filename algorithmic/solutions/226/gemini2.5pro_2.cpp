#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>
#include <map>

long long n;
long long x, y;

long long gcd(long long a, long long b) {
    while (b) {
        a %= b;
        std::swap(a, b);
    }
    return a;
}

namespace mat_exp {
    using matrix = std::vector<std::vector<long long>>;
    int size;
    const long long INF = -1e18;

    matrix multiply(const matrix& a, const matrix& b) {
        matrix c(size, std::vector<long long>(size, INF));
        for (int i = 0; i < size; ++i) {
            for (int j = 0; j < size; ++j) {
                for (int k = 0; k < size; ++k) {
                    if (a[i][k] != INF && b[k][j] != INF) {
                        c[i][j] = std::max(c[i][j], a[i][k] + b[k][j]);
                    }
                }
            }
        }
        return c;
    }

    matrix power(matrix base, long long exp) {
        matrix res(size, std::vector<long long>(size, INF));
        for (int i = 0; i < size; ++i) res[i][i] = 0;
        while (exp > 0) {
            if (exp % 2 == 1) res = multiply(res, base);
            base = multiply(base, base);
            exp /= 2;
        }
        return res;
    }
}


long long solve_mat_exp(long long m, long long xp, long long yp) {
    if (m <= 0) return 0;
    if (xp > yp) std::swap(xp, yp);

    int y_prime = yp;
    int x_prime = xp;

    std::vector<int> valid_masks;
    int limit = 1 << y_prime;
    for (int i = 0; i < limit; ++i) {
        if ((i & (i >> x_prime)) == 0) {
            valid_masks.push_back(i);
        }
    }

    int num_masks = valid_masks.size();
    mat_exp::size = num_masks;
    std::map<int, int> mask_to_idx;
    for (int i = 0; i < num_masks; ++i) {
        mask_to_idx[valid_masks[i]] = i;
    }

    mat_exp::matrix T(num_masks, std::vector<long long>(num_masks, mat_exp::INF));

    for (int i = 0; i < num_masks; ++i) {
        int u = valid_masks[i];
        
        // Case b=0 (don't pick current element)
        int v0 = (u << 1) & (limit - 1);
        if (mask_to_idx.count(v0)) {
            int v0_idx = mask_to_idx[v0];
            T[i][v0_idx] = std::max(T[i][v0_idx], 0LL);
        }

        // Case b=1 (pick current element)
        bool possible = true;
        if ((u & 1) != 0) possible = false; // conflict with i-y'
        if ((u & (1 << (y_prime - x_prime))) != 0) possible = false; // conflict with i-x'

        if (possible) {
            int v1 = v0 | 1;
            if (mask_to_idx.count(v1)) {
                int v1_idx = mask_to_idx[v1];
                T[i][v1_idx] = std::max(T[i][v1_idx], 1LL);
            }
        }
    }
    
    mat_exp::matrix T_m = mat_exp::power(T, m);
    
    std::vector<long long> dp_init(num_masks, mat_exp::INF);
    dp_init[mask_to_idx[0]] = 0;

    long long final_ans = 0;
    for(int i = 0; i < num_masks; ++i) {
        if (T_m[mask_to_idx[0]][i] != mat_exp::INF) {
            final_ans = std::max(final_ans, T_m[mask_to_idx[0]][i]);
        }
    }

    return final_ans;
}

int v2(long long val) {
    if (val == 0) return 63; // Undefined, but a large value works for comparison
    return __builtin_ctzll(val);
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    std::cin >> n >> x >> y;

    if ((x % 2 != 0) && (y % 2 != 0)) {
        long long ans = (n + 1) / 2;
        std::cout << ans << std::endl;
        return 0;
    }

    long long common_divisor = gcd(x, y);
    long long xp = x / common_divisor;
    long long yp = y / common_divisor;

    if (v2(x) == v2(y)) {
        long long g = common_divisor;
        long long rem = n % g;
        long long quot = n / g;
        long long ans = rem * ((quot + 1 + 1) / 2) + (g - rem) * ((quot + 1) / 2);
        std::cout << ans << std::endl;
        return 0;
    }

    if (std::max(xp, yp) > 20) {
        long long L_prime = xp + yp;
        unsigned __int128 num = n;
        num *= (L_prime / 2);
        num /= L_prime;
        long long ans = num;
        std::cout << ans << std::endl;
        return 0;
    }

    long long m1 = n / common_divisor + 1;
    long long m2 = n / common_divisor;
    long long c1 = n % common_divisor;
    long long c2 = common_divisor - c1;

    long long res1 = solve_mat_exp(m1, xp, yp);
    long long res2 = solve_mat_exp(m2, xp, yp);
    
    long long total_ans = c1 * res1 + c2 * res2;
    std::cout << total_ans << std::endl;

    return 0;
}