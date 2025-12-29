#include <iostream>
#include <string>
#include <unordered_map>
#include <vector>

// Function to send a "walk" command to the judge and receive the result.
int walk(long long x) {
    std::cout << "walk " << x << std::endl;
    int result;
    std::cin >> result;
    return result;
}

// Function to send a "guess" command to the judge.
void guess(long long g) {
    std::cout << "guess " << g << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    // The block size for the Baby-step Giant-step algorithm.
    // Optimal B is around sqrt(10^9) ~= 31623. We use 32000.
    const int B = 32000;

    // Determine the starting vertex. walk(0) reveals the current vertex without moving.
    int start_node = walk(0);

    // --- Phase 1: Baby steps ---
    // Take B steps of size 1. Store each new vertex and its distance from the start.
    std::unordered_map<int, int> baby_step_nodes;
    int current_node = start_node;
    for (int i = 1; i <= B; ++i) {
        current_node = walk(1);
        
        // If we return to the start, we have found n. This handles small n <= B.
        if (current_node == start_node) {
            guess(i);
            return 0;
        }

        // Store the first time we encounter a vertex to find the shortest path.
        if (baby_step_nodes.find(current_node) == baby_step_nodes.end()) {
            baby_step_nodes[current_node] = i;
        }
    }

    // At this point, the token is at a distance of B from the start_node.

    // --- Phase 2: Giant steps ---
    // Take B steps of size B. After each step, check for a collision with a baby-step node.
    for (int j = 1; j <= B; ++j) {
        current_node = walk(B);
        
        // Check if the current node was visited during the baby steps.
        if (baby_step_nodes.count(current_node)) {
            int i = baby_step_nodes[current_node];
            
            // A collision occurred.
            // Total distance from start after j giant steps is B (from baby steps) + j*B.
            // This position is the same as the one at distance i from the baby steps.
            // So, (B + j*B) is congruent to i modulo n.
            // (j+1)*B - i must be a multiple of n. The first collision gives n.
            long long n_candidate = (long long)(j + 1) * B - i;
            guess(n_candidate);
            return 0;
        }
    }

    return 0;
}