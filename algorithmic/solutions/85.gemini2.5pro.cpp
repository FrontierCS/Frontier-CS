#include <iostream>

int main() {
    // Fast I/O to prevent TLE in interactive problems
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int current_dist;
    std::cin >> current_dist;

    // Loop until we reach the exit (distance 0)
    while (current_dist > 0) {
        int res;
        int new_dist;

        // --- Try color 0 ---
        std::cout << "move 0" << std::endl;
        std::cin >> res;
        if (res == 1) {
            // Reached the exit, terminate
            break;
        }

        std::cout << "query" << std::endl;
        std::cin >> new_dist;
        if (new_dist < current_dist) {
            // Success: moved closer to the exit.
            // Update distance and start finding the path from the new node.
            current_dist = new_dist;
            continue;
        }
        
        // Failure: moved away from the exit. Backtrack to the previous node.
        std::cout << "move 0" << std::endl;
        std::cin >> res; // Result is not needed, we know we are not at the exit.

        // --- Try color 1 ---
        std::cout << "move 1" << std::endl;
        std::cin >> res;
        if (res == 1) {
            // Reached the exit
            break;
        }

        std::cout << "query" << std::endl;
        std::cin >> new_dist;
        if (new_dist < current_dist) {
            // Success: moved closer.
            current_dist = new_dist;
            continue;
        }
        
        // Failure: backtrack.
        std::cout << "move 1" << std::endl;
        std::cin >> res;

        // --- Deduce color 2 ---
        // If both color 0 and 1 lead away from the exit, color 2 must lead towards it.
        std::cout << "move 2" << std::endl;
        std::cin >> res;
        if (res == 1) {
            // Reached the exit
            break;
        }
        
        // We are now one step closer. Update the distance without a query.
        current_dist--;
    }

    return 0;
}