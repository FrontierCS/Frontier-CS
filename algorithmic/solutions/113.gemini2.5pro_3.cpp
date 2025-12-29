#include <iostream>
#include <vector>
#include <utility>
#include <cmath>

// A vector to store the sequence of moves.
// Each move is a pair of integers (from_basket, to_basket).
std::vector<std::pair<int, int>> moves;

/**
 * @brief Recursively generates moves to transfer N balls from a source basket to a destination basket.
 * 
 * This function implements the standard Tower of Hanoi algorithm.
 * 
 * @param n The number of balls to move.
 * @param src The source basket.
 * @param dest The destination basket.
 * @param aux The auxiliary basket.
 */
void solve(int n, int src, int dest, int aux) {
    if (n == 0) {
        return;
    }
    // Step 1: Move n-1 balls from source to auxiliary, using destination as temporary.
    solve(n - 1, src, aux, dest);
    
    // Step 2: Move the nth ball from source to destination.
    moves.push_back({src, dest});
    
    // Step 3: Move the n-1 balls from auxiliary to destination, using source as temporary.
    solve(n - 1, aux, dest, src);
}

int main() {
    // Fast I/O
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    
    int N;
    std::cin >> N;
    
    // Start the process to move N balls from basket 1 to basket 3, using basket 2 as auxiliary.
    solve(N, 1, 3, 2);
    
    // Output the total number of moves.
    std::cout << moves.size() << "\n";
    
    // Output each move.
    for (const auto& p : moves) {
        std::cout << p.first << " " << p.second << "\n";
    }
    
    return 0;
}