#include <iostream>
#include <cmath>

// This function implements the recursive solution to move n balls
// from the 'from' basket to the 'to' basket, using 'other' as auxiliary.
void solve(int n, int from, int to, int other) {
    if (n == 0) {
        return;
    }
    // Step 1: Move n-1 balls from 'from' to 'other'
    solve(n - 1, from, other, to);
    
    // Step 2: Move the nth ball from 'from' to 'to'
    std::cout << from << " " << to << "\n";
    
    // Step 3: Move n-1 balls from 'other' to 'to'
    solve(n - 1, other, to, from);
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    
    int n;
    std::cin >> n;
    
    // The total number of moves for N balls is 2^N - 1.
    // We use long long to avoid overflow for larger N, though for N > 20
    // the number of moves becomes very large to print within time limits.
    // This suggests test cases will have N small enough.
    long long moves = (1LL << n) - 1;
    std::cout << moves << "\n";
    
    // Start the process to move N balls from basket 1 to 3, using 2 as auxiliary.
    solve(n, 1, 3, 2);
    
    return 0;
}