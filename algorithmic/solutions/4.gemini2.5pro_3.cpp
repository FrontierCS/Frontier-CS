#include <iostream>
#include <vector>
#include <map>
#include <algorithm>
#include <cmath>

long long n;
long long k;

std::map<std::pair<int, int>, long long> cache;

// Function to query the matrix element at (r, c), with caching.
long long query(int r, int c) {
    if (r < 1 || r > n || c < 1 || c > n) {
        return -1; // Should not happen with valid logic
    }
    if (cache.count({r, c})) {
        return cache.at({r, c});
    }
    std::cout << "QUERY " << r << " " << c << std::endl;
    long long v;
    std::cin >> v;
    cache[{r, c}] = v;
    return v;
}

// Counts number of elements less than or equal to val in O(n) queries.
long long count_le(long long val) {
    long long count = 0;
    int r = 1;
    int c = n;
    while (r <= n && c >= 1) {
        long long v = query(r, c);
        if (v <= val) {
            count += c;
            r++;
        } else {
            c--;
        }
    }
    return count;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> n >> k;

    // Handle trivial cases
    if (k == 1) {
        std::cout << "DONE " << query(1, 1) << std::endl;
        return 0;
    }
    if (k == n * n) {
        std::cout << "DONE " << query(n, n) << std::endl;
        return 0;
    }

    long long low, high;
    
    // Heuristic to find a good initial range for binary search using the main diagonal.
    // The rank of a[i][i] is between i*i and n*n - (n-i+1)^2 + 1.
    std::vector<long long> diag(n + 1);
    for (int i = 1; i <= n; ++i) {
        diag[i] = query(i, i);
    }
    
    // Find i1, whose corresponding diagonal element a[i1][i1] is a candidate for a lower bound on the value.
    // Smallest i s.t. max_rank(a[i][i]) >= k
    int i1 = static_cast<int>(std::ceil(n + 1 - std::sqrt((long double)n * n - k + 1)));
    i1 = std::max(1, i1);

    // Find i2, whose corresponding diagonal element a[i2][i2] is a candidate for an upper bound.
    // Largest i s.t. min_rank(a[i][i]) <= k
    int i2 = static_cast<int>(std::floor(std::sqrt((long double)k)));
    i2 = std::min((int)n, i2);

    if (i1 > i2) {
        // Heuristic failed to find a valid range, fallback to full range.
        low = query(1, 1);
        high = query(n, n);
    } else {
        low = diag[i1];
        high = diag[i2];
    }
    
    // The heuristic might not give a guaranteed correct range.
    // Verify and expand to the full range if the k-th element is outside.
    if (count_le(low) >= k) {
         high = low;
         low = query(1, 1);
    }
    if (count_le(high) < k) {
        low = high;
        high = query(n, n);
    }
    
    long long ans = high;
    while (low <= high) {
        long long mid = low + (high - low) / 2;
        if (count_le(mid) >= k) {
            ans = mid;
            high = mid - 1;
        } else {
            low = mid + 1;
        }
    }

    std::cout << "DONE " << ans << std::endl;

    return 0;
}