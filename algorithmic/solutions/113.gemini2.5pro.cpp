#include <iostream>
#include <cmath>

// This function recursively generates the moves for the Tower of Hanoi problem.
// n: the number of balls to move
// from_basket: the source basket
// to_basket: the destination basket
// aux_basket: the auxiliary basket
void solve(int n, int from_basket, int to_basket, int aux_basket) {
    if (n == 0) {
        return;
    }
    // Step 1: Move n-1 balls from source to auxiliary, using destination as temporary.
    solve(n - 1, from_basket, aux_basket, to_basket);
    
    // Step 2: Move the nth ball from source to destination.
    std::cout << from_basket << " " << to_basket << "\n";
    
    // Step 3: Move the n-1 balls from auxiliary to destination, using source as temporary.
    solve(n - 1, aux_basket, to_basket, from_basket);
}

int main() {
    // Fast I/O
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int N;
    std::cin >> N;

    // The total number of moves for N balls in the Tower of Hanoi is 2^N - 1.
    // We use 1LL to ensure the calculation is done with 64-bit integers
    // to prevent overflow for larger N, although for N <= 30, int is sufficient for N
    // but the result can exceed int's capacity.
    long long num_moves = (1LL << N) - 1;
    std::cout << num_moves << "\n";

    // We only proceed to print moves if there are any balls to move.
    if (N > 0) {
        solve(N, 1, 3, 2);
    }

    return 0;
}