#include <iostream>
#include <vector>
#include <cmath>
#include <numeric>
#include <algorithm>

// Function to check if a number is prime
bool is_prime(int k) {
    if (k <= 1) return false;
    if (k <= 3) return true;
    if (k % 2 == 0 || k % 3 == 0) return false;
    for (int i = 5; i * i <= k; i = i + 6) {
        if (k % i == 0 || k % (i + 2) == 0)
            return false;
    }
    return true;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n_orig, m_orig;
    std::cin >> n_orig >> m_orig;

    int n = n_orig;
    int m = m_orig;
    bool swapped = false;
    if (n > m) {
        std::swap(n, m);
        swapped = true;
    }

    // Find the smallest prime q such that q*q >= m
    int q = 1;
    while (1LL * q * q < m) {
        q++;
    }
    while (!is_prime(q)) {
        q++;
    }
    
    std::vector<std::pair<int, int>> points;
    points.reserve(n * q);

    // Map rows to lines and columns to points in an affine plane over F_q.
    // Rows i are lines y = ax + b.
    // Columns j are points (x, y).
    // An optimized way is to iterate through rows, and for each line, find all points on it.
    for (int i = 0; i < n; ++i) {
        // Map row index i to a line y = a*x + b.
        // The mapping (i % q, i / q) is chosen to provide more diversity
        // for small i, compared to (i / q, i % q).
        long long a = i % q;
        long long b = i / q;
        
        // Iterate over all possible x coordinates in F_q.
        for (long long x = 0; x < q; ++x) {
            // Calculate the corresponding y coordinate on the line.
            long long y = (a * x + b) % q;
            
            // Map the point (x, y) back to a column index.
            // The mapping is (x, y) -> y*q + x.
            long long j_idx = y * q + x;
            
            // If the column index is within the m-bound, it's a valid point.
            if (j_idx < m) {
                if (!swapped) {
                    points.push_back({i + 1, static_cast<int>(j_idx) + 1});
                } else {
                    points.push_back({static_cast<int>(j_idx) + 1, i + 1});
                }
            }
        }
    }

    std::cout << points.size() << "\n";
    for (const auto& p : points) {
        std::cout << p.first << " " << p.second << "\n";
    }

    return 0;
}