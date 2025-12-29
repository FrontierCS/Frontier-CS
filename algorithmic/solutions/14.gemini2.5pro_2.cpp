#include <iostream>
#include <vector>
#include <string>
#include <map>
#include <cmath>
#include <numeric>
#include <algorithm>

// Function to interact with the judge for a "walk" operation.
// It sends the command and reads the returned vertex label.
// Exits if the judge returns -1 (error).
long long walk(long long x) {
    std::cout << "walk " << x << std::endl;
    long long result;
    std::cin >> result;
    if (result == -1) {
        exit(0);
    }
    return result;
}

// Function to interact with the judge for a "guess" operation.
// This ends the interaction.
void guess(long long g) {
    std::cout << "guess " << g << std::endl;
    exit(0);
}

// Helper function to get distinct prime factors of a number.
// Used in Phase 2 to find n from its multiple M.
std::vector<long long> get_prime_factors(long long n) {
    std::vector<long long> factors;
    for (long long i = 2; i * i <= n; ++i) {
        if (n % i == 0) {
            factors.push_back(i);
            while (n % i == 0) {
                n /= i;
            }
        }
    }
    if (n > 1) {
        factors.push_back(n);
    }
    return factors;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    long long s0 = walk(0);

    // Phase 1: Baby-step Giant-step to find a multiple M of n.
    // The block size B is chosen to be around sqrt(10^9) to balance
    // baby and giant steps for worst-case n.
    const int B = 32000;
    std::map<long long, int> visited;
    long long v_cur = s0;
    long long M = -1;
    long long v_meeting = -1;

    // Baby steps: walk 1 step at a time for B steps.
    // Store visited vertices and the number of steps to reach them.
    for (int i = 1; i <= B; ++i) {
        v_cur = walk(1);
        if (v_cur == s0) {
            M = i;
            v_meeting = s0;
            break;
        }
        // If we find a collision within baby steps
        if (visited.count(v_cur)) {
            M = i - visited[v_cur];
            v_meeting = v_cur;
            break;
        }
        visited[v_cur] = i;
    }

    if (M == -1) {
        // Giant steps: walk B steps at a time.
        // The number of giant steps needs to be enough for the largest possible n.
        // ceil(10^9 / B) is about 31250. B+1 is a safe upper bound.
        long long dist = B;
        for (int j = 1; j <= B + 1; ++j) {
            v_cur = walk(B);
            dist += B;
            if (v_cur == s0) {
                 M = dist;
                 v_meeting = s0;
                 break;
            }
            if (visited.count(v_cur)) {
                long long dist_baby = visited[v_cur];
                M = dist - dist_baby;
                v_meeting = v_cur;
                break;
            }
        }
    }
    
    // Phase 2: Find n from its multiple M.
    // We have M = k*n. We find n by "peeling off" prime factors from M
    // as long as the result is still a multiple of n.
    long long n_candidate = M;
    std::vector<long long> prime_factors = get_prime_factors(M);
    
    long long v_current = v_meeting;

    for (long long p : prime_factors) {
        while (n_candidate % p == 0) {
            long long test_dist = n_candidate / p;
            long long v_after_walk = walk(test_dist);
            if (v_after_walk == v_current) {
                // The walk brought us back, so n divides test_dist.
                // We can reduce our candidate for n.
                n_candidate = test_dist;
            } else {
                // The walk did not bring us back. n does not divide test_dist.
                // This means we have removed the correct number of factors of p from M.
                // We are now at a new vertex. To test the next prime, we must return.
                v_current = walk(n_candidate - test_dist);
                break;
            }
        }
    }

    guess(n_candidate);

    return 0;
}