#include <iostream>
#include <vector>
#include <string>
#include <cmath>

// A vector to store the sequence of moves.
std::vector<std::pair<int, int>> moves;

/**
 * @brief Recursive function to solve the ball-moving puzzle using a Tower of Hanoi approach.
 * 
 * @param n The number of balls to move.
 * @param from_basket The source basket.
 * @param to_basket The destination basket.
 * @param aux_basket The auxiliary basket.
 */
void solve(int n, int from_basket, int to_basket, int aux_basket) {
    if (n == 0) {
        return;
    }
    // Move n-1 balls from the source to the auxiliary basket, using the destination as temporary.
    solve(n - 1, from_basket, aux_basket, to_basket);
    
    // Record the move of the n-th ball from the source to the destination.
    moves.push_back({from_basket, to_basket});
    
    // Move the n-1 balls from the auxiliary basket to the destination, using the source as temporary.
    solve(n - 1, aux_basket, to_basket, from_basket);
}

int main() {
    // Optimize standard I/O for faster execution.
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    // The initial call to solve the problem for N balls from basket 1 to 3, using 2 as auxiliary.
    solve(n, 1, 3, 2);

    // Output the total number of moves.
    std::cout << moves.size() << "\n";
    
    // Output each move in the sequence.
    for (const auto& move : moves) {
        std::cout << move.first << " " << move.second << "\n";
    }

    return 0;
}