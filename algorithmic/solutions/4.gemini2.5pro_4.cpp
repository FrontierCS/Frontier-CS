#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <map>

// Using a map for memoization for queried cell values.
std::map<std::pair<int, int>, long long> memo;
long long n_val;

// Function to perform a query and cache the result.
long long do_query(int r, int c) {
    if (memo.count({r, c})) {
        return memo[{r, c}];
    }
    std::cout << "QUERY " << r << " " << c << std::endl;
    long long v;
    std::cin >> v;
    if (std::cin.fail()) {
        // In case of an error from the judge or unexpected termination.
        exit(0);
    }
    return memo[{r, c}] = v;
}

// Counts the number of elements in the matrix less than or equal to `val`.
// This uses a "staircase" search pattern, making at most 2n new queries.
long long count_le(long long val) {
    long long count = 0;
    int c = n_val;
    for (int r = 1; r <= n_val; ++r) {
        while (c > 0 && do_query(r, c) > val) {
            c--;
        }
        count += c;
    }
    return count;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    long long k_val;
    std::cin >> n_val >> k_val;

    long long lo, hi;

    if (n_val > 0) {
        // Initialize search range with min and max possible values.
        lo = do_query(1, 1);
        hi = do_query(n_val, n_val);
    } else {
        // Edge case for n=0, though constraints likely prevent this.
        std::cout << "DONE " << 0 << std::endl;
        return 0;
    }

    long long ans = hi;

    // Binary search for the k-th smallest value.
    while (lo <= hi) {
        long long mid = lo + (hi - lo) / 2;
        
        if (count_le(mid) >= k_val) {
            ans = mid;
            hi = mid - 1;
        } else {
            lo = mid + 1;
        }
    }

    std::cout << "DONE " << ans << std::endl;

    return 0;
}