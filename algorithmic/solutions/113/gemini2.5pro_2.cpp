#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>

std::vector<int> baskets[4];
std::vector<std::pair<int, int>> moves;

void perform_move(int from, int to) {
    // Determine the center ball based on the rules.
    // In a sorted list of k balls (1-indexed), the position is (k+2)/2.
    int k = baskets[from].size();
    int center_1_based_idx = (k + 2) / 2;
    int ball_to_move = baskets[from][center_1_based_idx - 1];
    
    // Find and remove the ball from the 'from' basket.
    // std::lower_bound works because the vector is sorted.
    auto it = std::lower_bound(baskets[from].begin(), baskets[from].end(), ball_to_move);
    baskets[from].erase(it);
    
    // Add the ball to the 'to' basket and re-sort to maintain order.
    baskets[to].push_back(ball_to_move);
    std::sort(baskets[to].begin(), baskets[to].end());
    
    // Record the move.
    moves.push_back({from, to});
}

void hanoi(int n, int from, int to, int via) {
    if (n == 0) {
        return;
    }
    // The core Tower of Hanoi recursion.
    // The parameter 'n' does not directly pick a ball, but controls the recursion depth
    // and the sequence of basket operations.
    hanoi(n - 1, from, via, to);
    perform_move(from, to);
    hanoi(n - 1, via, to, from);
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    
    int N;
    std::cin >> N;
    
    // Initially, all N balls are in basket 1.
    baskets[1].resize(N);
    std::iota(baskets[1].begin(), baskets[1].end(), 1);
    
    // Start the process to move N balls from basket 1 to 3, using 2 as auxiliary.
    hanoi(N, 1, 3, 2);
    
    std::cout << moves.size() << "\n";
    for (const auto& move : moves) {
        std::cout << move.first << " " << move.second << "\n";
    }
    
    return 0;
}