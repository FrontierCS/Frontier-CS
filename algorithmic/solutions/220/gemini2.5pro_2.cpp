#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

// Function to check if all players are solid
bool is_solved(int n, const std::vector<std::vector<int>>& counts) {
    for (int i = 1; i <= n; ++i) {
        if (counts[i][i] != n) {
            return false;
        }
    }
    return true;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    std::vector<std::vector<int>> counts(n + 1, std::vector<int>(n + 1, 0));
    for (int i = 1; i <= n; ++i) {
        for (int j = 0; j < n; ++j) {
            int card;
            std::cin >> card;
            counts[i][card]++;
        }
    }

    std::vector<std::vector<int>> history;

    while (!is_solved(n, counts)) {
        std::vector<int> move(n + 1);
        std::vector<bool> value_taken(n + 1, false);

        // Find a perfect matching greedily with a preferred card order for each player.
        // This ensures that we can always find a set of cards to pass.
        for (int p = 1; p <= n; ++p) {
            for (int j = 0; j < n; ++j) {
                // Preferred card to pass is (p+1), then (p+2), etc. (modulo n, 1-based).
                // The last preference is p itself.
                // Formula for 1-based player p and 0-based preference index j:
                // v = (p-1 + j+1) % n + 1 = (p+j) % n + 1
                int v = (p + j) % n + 1;
                
                if (counts[p][v] > 0 && !value_taken[v]) {
                    move[p] = v;
                    value_taken[v] = true;
                    break;
                }
            }
        }
        
        history.push_back(move);

        // Update card counts based on the move.
        // First, remove the passed cards from players' hands.
        for (int p = 1; p <= n; ++p) {
            counts[p][move[p]]--;
        }

        // Then, add the received cards to players' hands.
        for (int p = 1; p <= n; ++p) {
            int receiver = (p % n) + 1;
            counts[receiver][move[p]]++;
        }
    }

    std::cout << history.size() << "\n";
    for (const auto& move : history) {
        for (int p = 1; p <= n; ++p) {
            std::cout << move[p] << (p == n ? "" : " ");
        }
        std::cout << "\n";
    }

    return 0;
}