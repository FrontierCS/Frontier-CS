#include <iostream>
#include <vector>
#include <string>
#include <map>
#include <algorithm>

// Function to set up fast I/O
void fast_io() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
}

// Calculates the power of a spell formed by w_u and w_v
// where w_i = X^A O^i. The concatenated string is X^A O^{Bu} X^A O^{Bv}.
// Bu and Bv are the number of 'O's, which correspond to the indices u and v.
long long calculate_power(long long A, long long Bu, long long Bv) {
    long long p = A;
    p += (A + 1) * std::max(Bu, Bv);
    p += A * (A + 1) * Bu;
    p += A * (A + 1) * Bu * Bv;
    return p;
}

int main() {
    fast_io();

    int n;
    std::cin >> n;

    // A must be large enough to guarantee uniqueness. A > n-1 is sufficient.
    // We choose A = n + 1.
    // The number of 'O's, B_i, is set to i.
    int A = n + 1;

    // Part 1: Output n magic words
    for (int i = 1; i <= n; ++i) {
        std::string s(A, 'X');
        s.append(i, 'O');
        std::cout << s << "\n";
    }
    std::cout.flush();

    // Precompute the power for all n*n possible pairs (u, v)
    // and store them in a map for quick lookups.
    std::map<long long, std::pair<int, int>> power_map;
    for (int u = 1; u <= n; ++u) {
        for (int v = 1; v <= n; ++v) {
            long long p = calculate_power(A, u, v);
            power_map[p] = {u, v};
        }
    }

    // Part 2: Answer q queries
    int q;
    std::cin >> q;
    while (q--) {
        long long p_query;
        std::cin >> p_query;
        auto res = power_map.at(p_query);
        std::cout << res.first << " " << res.second << "\n";
        std::cout.flush();
    }

    return 0;
}