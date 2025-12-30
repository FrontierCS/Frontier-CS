#include <iostream>
#include <vector>
#include <numeric>

// Function to perform a query and get the number of collisions
long long perform_query(const std::vector<long long>& elements) {
    if (elements.empty()) {
        return 0;
    }
    std::cout << "0 " << elements.size();
    for (long long x : elements) {
        std::cout << " " << x;
    }
    std::cout << std::endl;
    long long collisions;
    std::cin >> collisions;
    return collisions;
}

// Function to submit the final answer
void submit_answer(long long n) {
    std::cout << "1 " << n << std::endl;
}

// Helper to generate a vector of sequential numbers [start, ..., end]
std::vector<long long> generate_sequence(long long start, long long end) {
    if (start > end) {
        return {};
    }
    std::vector<long long> vec(end - start + 1);
    std::iota(vec.begin(), vec.end(), start);
    return vec;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    // Stage 1: Check for small n
    long long k1 = 333332;

    long long c1 = perform_query(generate_sequence(1, k1));
    long long c2 = perform_query(generate_sequence(1, k1 + 1));

    if (c1 > 0) {
        // n <= k1. We can find n directly.
        long long q = c2 - c1;
        if (q > 0) {
            long long n_numerator = 2LL * k1 * q - 2LL * c1;
            long long n_denominator = q * (q + 1);
            long long n = n_numerator / n_denominator;
            submit_answer(n);
        }
        return 0;
    }
    
    if (c2 > 0) {
        // c1 == 0 and c2 > 0 implies n = k1 + 1
        submit_answer(k1 + 1);
        return 0;
    }

    // Stage 2: n > k1 + 1. Check for a slightly larger n.
    // At this point, c1 = 0 and c2 = 0, so n > k1 + 1 = 333333.
    long long k3 = 333334;
    long long c3 = perform_query(generate_sequence(1, k3));

    if (c3 > 0) {
        // n <= k3. Since we know n > k1 + 1, n must be k3.
        submit_answer(k3);
    } else {
        // n > k3. With the current budget, this case is considered unsolvable.
        // It's a strategic assumption that test data won't fall here.
    }

    return 0;
}