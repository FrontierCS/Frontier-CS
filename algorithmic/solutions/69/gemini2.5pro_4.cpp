#include <iostream>
#include <vector>
#include <string>
#include <map>
#include <algorithm>

// Calculates the power of a string of the form X^A O X^B O X^C,
// assuming A, B, C are from carefully chosen disjoint integer ranges
// and satisfy A < C < B.
long long calculate_power(long long A, long long B, long long C) {
    return A * B + B * C + A + 3 * B + C + 2;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    // Use long long for a and b to prevent overflow in power calculation.
    std::vector<long long> a(n + 1), b(n + 1);
    
    // To ensure A < C < B and break symmetry in the power function,
    // we choose a_i as a linear function of i and b_i as another
    // different linear function of i.
    // Let a_i = C1 + i, b_i = C2 + 2i. We need to select C1, C2
    // to ensure A, B, C value ranges do not overlap.
    // Let n_max = 1000.
    // a_i = 2500 + i. A = 2500 + u. Range: [2501, 3500]
    // b_i = 5000 + 2i. C = 5000 + 2v. Range: [5002, 7000]
    // B = b_u + a_v = 5000+2u + 2500+v = 7500+2u+v. Range: [7503, 10500]
    // The condition A < C < B is always satisfied for n <= 1000.
    long long C1 = 2 * n + 500;
    if (n > 500) C1 = 2 * n + 1500;
    long long C2 = 2 * C1;

    for (int i = 1; i <= n; ++i) {
        a[i] = C1 + i;
        b[i] = C2 + 2LL * i;
    }

    for (int i = 1; i <= n; ++i) {
        std::string w_i = std::string(a[i], 'X') + 'O' + std::string(b[i], 'X');
        std::cout << w_i << "\n";
    }
    std::cout << std::flush;

    int q;
    std::cin >> q;
    for (int j = 0; j < q; ++j) {
        long long p_query;
        std::cin >> p_query;

        bool found = false;
        for (int u = 1; u <= n; ++u) {
            int low = 1, high = n, ans_v = -1;
            while (low <= high) {
                int mid_v = low + (high - low) / 2;
                long long cur_A = a[u];
                long long cur_C = b[mid_v];
                long long cur_B = b[u] + a[mid_v];
                
                long long p_calc = calculate_power(cur_A, cur_B, cur_C);

                if (p_calc == p_query) {
                    ans_v = mid_v;
                    break;
                }
                if (p_calc < p_query) {
                    low = mid_v + 1;
                } else {
                    high = mid_v - 1;
                }
            }
            if (ans_v != -1) {
                std::cout << u << " " << ans_v << "\n";
                std::cout << std::flush;
                found = true;
                break;
            }
        }
    }

    return 0;
}