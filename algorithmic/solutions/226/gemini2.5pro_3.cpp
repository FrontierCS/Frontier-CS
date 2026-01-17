#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>

long long n;
long long x, y;

long long gcd(long long a, long long b) {
    while (b) {
        a %= b;
        std::swap(a, b);
    }
    return a;
}

// Matrix for max-plus algebra
using matrix = std::vector<std::vector<long long>>;
const long long INF = -1e18;

matrix multiply(const matrix& a, const matrix& b, int size) {
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

matrix matrix_pow(matrix base, long long exp) {
    int size = base.size();
    matrix result(size, std::vector<long long>(size, INF));
    for (int i = 0; i < size; ++i) {
        result[i][i] = 0;
    }
    while (exp > 0) {
        if (exp % 2 == 1) {
            result = multiply(result, base, size);
        }
        base = multiply(base, base, size);
        exp /= 2;
    }
    return result;
}

long long solve_dp(long long m, long long xp, long long yp) {
    if (m == 0) return 0;
    
    int L = yp;
    int size = 1 << L;
    matrix T(size, std::vector<long long>(size, INF));

    for (int mask = 0; mask < size; ++mask) {
        // Option 1: don't take the current element i
        int next_mask0 = (mask << 1) & (size - 1);
        T[next_mask0][mask] = 0;

        // Option 2: take the current element i
        bool possible = true;
        // Check conflict with i-xp
        if ((mask >> (L - xp)) & 1) {
            possible = false;
        }
        // Check conflict with i-yp
        if ((mask >> (L - yp)) & 1) { // same as (mask >> 0) & 1
            possible = false;
        }

        if (possible) {
            int next_mask1 = ((mask << 1) & (size - 1)) | 1;
            T[next_mask1][mask] = 1;
        }
    }
    
    matrix T_m = matrix_pow(T, m);
    
    long long max_val = 0;
    // Initial state is dp[0][mask=0] = 0. So we look at T_m[...][0]
    for(int i = 0; i < size; ++i) {
        max_val = std::max(max_val, T_m[i][0]);
    }

    return max_val;
}

long long solve_approx(long long m, long long xp, long long yp) {
    if (m <= 0) return 0;
    if ((xp % 2 != 0) && (yp % 2 != 0)) {
        return (m + 1) / 2;
    }
    long double L = xp + yp;
    long double density = floor(L / 2.0L) / L;
    return static_cast<long long>(m * density + 0.5L);
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    std::cin >> n >> x >> y;

    long long common_divisor = gcd(x, y);
    long long xp = x / common_divisor;
    long long yp = y / common_divisor;
    
    if (xp > yp) std::swap(xp, yp);

    long long q = n / common_divisor;
    long long rem = n % common_divisor;

    long long ans = 0;
    if (yp <= 15) {
        long long f_q = solve_dp(q, xp, yp);
        long long f_q1 = solve_dp(q + 1, xp, yp);
        ans = rem * f_q1 + (common_divisor - rem) * f_q;
    } else {
        long long f_q = solve_approx(q, xp, yp);
        long long f_q1 = solve_approx(q + 1, xp, yp);
        ans = rem * f_q1 + (common_divisor - rem) * f_q;
    }
    
    std::cout << ans << std::endl;

    return 0;
}