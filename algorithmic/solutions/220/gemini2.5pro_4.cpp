#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

// Using 0-based indexing for players [0, n-1] and 1-based for cards [1, n].
// Player (i+1)%n sits to the right of player i.
// Player i passes a card to player (i+1)%n.
// The goal is for player i to have n cards with value i+1.

// This function checks if all players are in a "solid" state.
// A player i is solid if all their cards have the value i+1.
bool is_solid(int n, const std::vector<std::vector<int>>& counts) {
    for (int i = 0; i < n; ++i) {
        if (counts[i][i + 1] != n) {
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

    // counts[i][j] stores the number of cards with value j player i has.
    // Player indices are 0 to n-1. Card values are 1 to n.
    std::vector<std::vector<int>> counts(n, std::vector<int>(n + 1, 0));
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            int card;
            std::cin >> card;
            counts[i][card]++;
        }
    }

    std::vector<std::vector<int>> operations;

    // The problem guarantees a solution exists in at most n^2-n operations.
    // We simulate step-by-step until the solid state is reached.
    while (!is_solid(n, counts)) {
        std::vector<int> passes(n);
        for (int i = 0; i < n; ++i) {
            // Strategy: each player passes the card that is "farthest" from its target player.
            // Player i (0-indexed) wants to become solid with cards of value i+1.
            // A card 'c' (1-indexed) has a target player 'c-1'.
            // When card 'c' is at player 'i', its distance to its target is the number of
            // rightward passes needed: ((c-1) - i + n) % n.
            // We want to pass the card that maximizes this distance.
            
            int best_card_to_pass = -1;
            
            // Iterate through possible distances from maximum (n-1) down to 0.
            for (int d = n - 1; d >= 0; --d) {
                // For a given player i and distance d, the corresponding card value c can be calculated.
                // dist = ((c-1) - i + n) % n
                // c-1 = (dist + i) % n
                // c = (dist + i) % n + 1
                int card_to_check = (i + d) % n + 1;
                if (counts[i][card_to_check] > 0) {
                    best_card_to_pass = card_to_check;
                    break; // Found the card with the largest distance, this is the one to pass.
                }
            }
            // A player always has n cards, so some card will always be found.
            // If player i is solid, they only have card i+1.
            // The distance for card i+1 is ((i+1-1)-i+n)%n = 0.
            // So the loop for d will find it when d=0.
            passes[i] = best_card_to_pass;
        }
        operations.push_back(passes);

        // All passes happen simultaneously. We calculate the next state based on the current one.
        std::vector<int> passed_cards = passes;
        for (int i = 0; i < n; ++i) {
            // Player i passes their chosen card.
            counts[i][passed_cards[i]]--;
            
            // Player i receives a card from the player to their left.
            // The player to the left of i is (i - 1 + n) % n.
            int from_player = (i - 1 + n) % n;
            counts[i][passed_cards[from_player]]++;
        }
    }

    std::cout << operations.size() << "\n";
    for (const auto& op : operations) {
        for (int i = 0; i < n; ++i) {
            std::cout << op[i] << (i == n - 1 ? "" : " ");
        }
        std::cout << "\n";
    }

    return 0;
}