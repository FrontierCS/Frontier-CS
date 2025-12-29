#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>

// Function to send a query to the interactor
long long query(const std::vector<long long>& q) {
    if (q.empty()) {
        return 0;
    }
    std::cout << "0 " << q.size();
    for (long long x : q) {
        std::cout << " " << x;
    }
    std::cout << std::endl;
    long long collisions;
    std::cin >> collisions;
    if (collisions == -1) exit(0);
    return collisions;
}

// Function to submit the final answer
void answer(long long n) {
    std::cout << "1 " << n << std::endl;
}

// Memoization for collision queries to reduce cost
std::map<long long, long long> memo;

// A helper function to query for collisions between two arithmetic progressions
// S1 = {L+1, ..., L+k} and S2 = {L+d+1, ..., L+d+k}
// For n > k, this gives k - (d mod n) if d mod n < k, and 0 otherwise.
long long get_collisions(long long d, int k) {
    if (memo.count(d)) {
        return memo[d];
    }
    const long long L = 200000000000000000LL; 
    std::vector<long long> q;
    q.reserve(2 * k);
    for (int i = 1; i <= k; ++i) {
        q.push_back(L + i);
    }
    for (int i = 1; i <= k; ++i) {
        q.push_back(L + d + i);
    }
    return memo[d] = query(q);
}

// Function to find d mod n using binary search and collision queries
long long find_rem(long long d, int k) {
    long long low = 0, high = d;
    long long rem_lb = 0;
    
    // The set of m for which get_collisions(d-m, k) > 0 is expected to be
    // {m | (d-m) mod n < k}. This corresponds to m mod n being in (rem-k, rem].
    // We binary search for the largest such m, which should be rem itself.
    if (get_collisions(d, k) > 0) {
        rem_lb = 0; // The range of m with collisions starts at or before 0
    }
    
    // Find the largest m in [0, d] such that a collision occurs for d-m
    while(low <= high) {
        long long mid = low + (high-low)/2;
        if (get_collisions(d-mid,k) > 0) {
            rem_lb = mid;
            low = mid + 1;
        } else {
            high = mid-1;
        }
    }
    
    long long colls = get_collisions(d - rem_lb, k);
    return rem_lb + k - colls;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    // Phase 1: Handle small n
    const int K_small = 450;
    std::vector<long long> small_q;
    for (int i = 1; i <= K_small; ++i) {
        small_q.push_back(i);
    }

    if (query(small_q) > 0) {
        int low = 1, high = K_small;
        int k0 = K_small;
        while (low <= high) {
            int mid = low + (high - low) / 2;
            if (mid == 0) {
                low = 1;
                continue;
            }
            std::vector<long long> q;
            for (int i = 1; i <= mid; ++i) {
                q.push_back(i);
            }
            if (query(q) > 0) {
                k0 = mid;
                high = mid - 1;
            } else {
                low = mid + 1;
            }
        }
        answer(k0 - 1);
        return 0;
    }

    // Phase 2: Handle large n
    const int K_large = 400;
    std::vector<long long> r(35);

    // Find (2^i mod n) for i up to 33
    for (int i = 0; i <= 33; ++i) {
        memo.clear();
        r[i] = find_rem(1LL << i, K_large);
    }

    // Recover n from the remainders.
    // We have 2 * (2^i mod n) = (2^{i+1} mod n) + c*n, where c is 0 or 1.
    // So, 2*r[i] - r[i+1] will be either 0 or n.
    // The first non-zero value must be n.
    for (int i = 0; i <= 32; ++i) {
        long long candidate_n = 2 * r[i] - r[i+1];
        if (candidate_n > 0) {
            answer(candidate_n);
            return 0;
        }
    }

    return 0;
}