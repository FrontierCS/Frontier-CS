#include <iostream>

int main() {
    // The problem asks for a map where random moves fail to synchronize all agents.
    // A long path (snake/boustrophedon pattern) maximizes the expected time to merge 
    // all agents into a single cell, as it behaves like a random walk on a line 
    // which requires O(L^2) time to mix, and much longer to synchronize all N agents.
    // With N=20, M=20, we can construct a path of length ~210.
    
    std::cout << "20 20" << std::endl;
    for (int i = 0; i < 20; ++i) {
        if (i % 2 == 0) {
            // Even rows are full corridors (all '1's)
            std::cout << "11111111111111111111" << std::endl;
        } else {
            // Odd rows act as turns/connectors
            // We alternate the connection side:
            // Row 1 connects at the Right (col 19)
            // Row 3 connects at the Left (col 0)
            // This forms a continuous snake path covering the grid.
            if (i % 4 == 1) {
                std::cout << "00000000000000000001" << std::endl;
            } else {
                std::cout << "10000000000000000000" << std::endl;
            }
        }
    }
    return 0;
}