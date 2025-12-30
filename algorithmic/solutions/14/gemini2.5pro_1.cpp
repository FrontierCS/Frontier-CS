#include <iostream>
#include <vector>
#include <string>
#include <map>
#include <cmath>

// Function to interact with the judge by issuing a "walk" command.
int walk(long long x) {
    std::cout << "walk " << x << std::endl;
    int v;
    std::cin >> v;
    return v;
}

// Function to interact with the judge by issuing a "guess" command.
void guess(long long g) {
    std::cout << "guess " << g << std::endl;
}

int main() {
    // Use fast I/O.
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    // The block size for the Baby-step Giant-step algorithm.
    // Chosen to be near sqrt(10^9) to minimize the total number of queries.
    const int B = 32000;

    // A map to store vertices seen and the number of steps to reach them.
    std::map<int, int> seen;
    
    // Get the starting vertex label by walking 0 steps. This corresponds to 0 total steps.
    int current_v = walk(0);
    seen[current_v] = 0;

    // Phase 1: Baby steps.
    // Take B steps of size 1.
    for (int j = 1; j <= B; ++j) {
        current_v = walk(1);
        if (seen.count(current_v)) {
            // A collision occurred during baby steps, which means n is small.
            // The cycle length is the difference in steps.
            guess(j - seen[current_v]);
            return 0;
        }
        seen[current_v] = j;
    }

    // Phase 2: Giant steps.
    // If no cycle was found, n > B. We are at a total distance of B.
    // Now, take giant steps of size B.
    long long total_steps = B;
    // The loop for giant steps. With B=32000, i can go up to ~31250 for n=10^9.
    // Looping to B+2 provides a safe upper bound.
    for (int i = 2; i <= B + 2; ++i) {
        current_v = walk(B);
        total_steps += B;
        if (seen.count(current_v)) {
            // A giant step landed on a vertex seen during baby steps.
            // The difference in total steps gives us n.
            int j = seen[current_v];
            guess(total_steps - j);
            return 0;
        }
    }

    // This part of the code should be unreachable given the problem constraints.
    return 0;
}