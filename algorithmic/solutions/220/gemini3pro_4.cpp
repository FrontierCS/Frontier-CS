#include <iostream>
#include <vector>

using namespace std;

int main() {
    // Optimize standard I/O operations for speed
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    // cnt[i][v] stores the number of cards with value v held by player i
    // Using 0-based indexing for logic: players 0..n-1, card values 0..n-1
    // The input gives 1-based values, we convert to 0-based immediately.
    vector<vector<int>> cnt(n, vector<int>(n, 0));

    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            int val;
            cin >> val;
            cnt[i][val - 1]++;
        }
    }

    struct Move {
        vector<int> passed_cards;
    };
    vector<Move> history;
    
    // We reserve memory to avoid reallocations during the loop
    history.reserve(n * n);

    // The problem statement guarantees a solution within n*(n-1) operations.
    // We allow checking up to this limit.
    int max_ops = n * (n - 1);
    
    for (int step = 0; step <= max_ops; ++step) {
        // Check if the current configuration is solved
        // A player i is solid if they have n cards of value i (which is their index)
        bool solved = true;
        for (int i = 0; i < n; ++i) {
            if (cnt[i][i] != n) {
                solved = false;
                break;
            }
        }
        if (solved) break;
        
        // If we have performed max_ops and still not solved (should not happen per problem guarantee), stop.
        if (step == max_ops) break;

        Move current_move;
        current_move.passed_cards.resize(n);

        // Determine the card to pass for each player
        // Greedy Strategy:
        // Each player passes a card that minimizes the distance to its target owner.
        // Distance d for card value v at player i is defined such that (i + d) % n == v.
        // We prioritize passing cards with d > 0 (cards that don't belong to current player).
        // Among those, we pick the one with the smallest d.
        // This effectively moves cards to their destinations as quickly as possible.
        // If a player only has cards belonging to themselves (d=0), they are forced to pass one.
        
        for (int i = 0; i < n; ++i) {
            int best_val = -1;
            
            // Check for cards with distance 1, then 2, ..., up to n-1
            for (int d = 1; d < n; ++d) {
                int target_card = (i + d) % n;
                if (cnt[i][target_card] > 0) {
                    best_val = target_card;
                    break; // Found the best candidate
                }
            }

            if (best_val == -1) {
                // Player only has cards of value i (distance 0)
                best_val = i;
            }

            current_move.passed_cards[i] = best_val;
        }

        // Apply the determined moves simultaneously
        // 1. Decrement counts for senders
        for (int i = 0; i < n; ++i) {
            cnt[i][current_move.passed_cards[i]]--;
        }
        // 2. Increment counts for receivers
        // Player i passes to (i + 1) % n
        for (int i = 0; i < n; ++i) {
            int next_player = (i + 1) % n;
            cnt[next_player][current_move.passed_cards[i]]++;
        }

        history.push_back(current_move);
    }

    // Output the result
    cout << history.size() << "\n";
    for (const auto& m : history) {
        for (int i = 0; i < n; ++i) {
            // Convert back to 1-based indexing for output
            cout << m.passed_cards[i] + 1 << (i == n - 1 ? "" : " ");
        }
        cout << "\n";
    }

    return 0;
}