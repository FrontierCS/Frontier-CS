#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

// Calculates the change in the sum of squared differences for an operation (i, j)
long long calculate_delta_s2(long long Ai, long long Bi, long long Aj, long long Bj) {
    long long di = Ai - Bi;
    long long dj = Aj - Bj;
    long long Ai_new = Aj - 1;
    long long Aj_new = Ai + 1;
    long long di_new = Ai_new - Bi;
    long long dj_new = Aj_new - Bj;
    return di_new * di_new + dj_new * dj_new - di * di - dj * dj;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    int n;
    std::cin >> n;
    std::vector<long long> a(n), b(n);
    long long sum_a = 0, sum_b = 0;
    for (int i = 0; i < n; ++i) {
        std::cin >> a[i];
        sum_a += a[i];
    }
    for (int i = 0; i < n; ++i) {
        std::cin >> b[i];
        sum_b += b[i];
    }

    if (sum_a != sum_b) {
        std::cout << "No" << std::endl;
        return 0;
    }

    std::vector<std::pair<int, int>> ops;
    
    // Safety break; based on constraints and problem type, this limit should be sufficient.
    for (int k = 0; k < 40000; ++k) {
        bool done = true;
        for (int i = 0; i < n; ++i) {
            if (a[i] != b[i]) {
                done = false;
                break;
            }
        }
        if (done) {
            break;
        }

        long long best_delta = 0;
        int best_i = -1, best_j = -1;

        for (int i = 0; i < n; ++i) {
            for (int j = i + 1; j < n; ++j) {
                long long delta = calculate_delta_s2(a[i], b[i], a[j], b[j]);
                if (delta < best_delta) {
                    best_delta = delta;
                    best_i = i;
                    best_j = j;
                }
            }
        }
        
        if (best_i != -1) {
            ops.push_back({best_i + 1, best_j + 1});
            long long temp_ai = a[best_i];
            long long temp_aj = a[best_j];
            a[best_i] = temp_aj - 1;
            a[best_j] = temp_ai + 1;
        } else {
            // If A != B, there must be a way to decrease sum of squares.
            // If we are in a local minimum where all deltas are non-negative,
            // this strategy fails. However, for this problem, it's likely
            // always possible to find a negative delta unless A=B.
            break; 
        }
    }

    bool possible = true;
    for (int i = 0; i < n; ++i) {
        if (a[i] != b[i]) {
            possible = false;
            break;
        }
    }

    if (possible) {
        std::cout << "Yes" << std::endl;
        std::cout << ops.size() << std::endl;
        for (const auto& p : ops) {
            std::cout << p.first << " " << p.second << std::endl;
        }
    } else {
        std::cout << "No" << std::endl;
    }

    return 0;
}