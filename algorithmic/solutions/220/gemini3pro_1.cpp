#include <iostream>
#include <vector>

using namespace std;

// cnt[player][card_value]
// Stores how many cards of a specific value a player holds.
// Constraints: n <= 100, so 105 is sufficient.
int cnt[105][105];

int main() {
    // Optimize I/O operations for speed
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    for (int i = 1; i <= n; ++i) {
        for (int j = 0; j < n; ++j) {
            int c;
            cin >> c;
            cnt[i][c]++;
        }
    }

    // According to the problem statement, a solution exists within n*(n-1) operations.
    int limit = n * (n - 1);
    vector<vector<int>> history;
    history.reserve(limit);

    // Simulation loop
    for (int step = 0; step <= limit; ++step) {
        // Check if all players are solid (each player i holds n cards of value i)
        bool solid = true;
        for (int i = 1; i <= n; ++i) {
            if (cnt[i][i] != n) {
                solid = false;
                break;
            }
        }

        // If solid, print the sequence of operations and exit
        if (solid) {
            cout << step << "\n";
            for (const auto& move : history) {
                for (int i = 0; i < n; ++i) {
                    cout << move[i] << (i == n - 1 ? "" : " ");
                }
                cout << "\n";
            }
            return 0;
        }

        // If we reached the limit and are not solid, stop (though guarantee says this won't happen)
        if (step == limit) break;

        vector<int> moves(n);
        // Determine the card each player passes
        for (int i = 1; i <= n; ++i) {
            int best_val = -1;
            // Strategy: Pass the card that has the smallest non-zero distance to its target.
            // A card 'val' at player 'i' needs to travel d steps to reach player 'val'.
            // The distance is d = (val - i + n) % n.
            // We iterate d from 1 to n-1 to find if the player holds such a card.
            // Given i and d, the card value is uniquely determined as val = (i + d - 1) % n + 1.
            for (int d = 1; d < n; ++d) {
                int val = (i + d - 1) % n + 1;
                if (cnt[i][val] > 0) {
                    best_val = val;
                    break;
                }
            }
            // If the player only has cards with distance 0 (i.e., only cards of value i),
            // they are forced to pass one of them.
            if (best_val == -1) {
                best_val = i;
            }
            moves[i - 1] = best_val;
        }

        // Apply moves simultaneously
        // First, decrement counts for cards leaving their current owners
        for (int i = 1; i <= n; ++i) {
            cnt[i][moves[i - 1]]--;
        }
        // Then, increment counts for cards arriving at the next player (i -> i+1)
        for (int i = 1; i <= n; ++i) {
            int next_p = (i % n) + 1;
            cnt[next_p][moves[i - 1]]++;
        }

        history.push_back(moves);
    }

    return 0;
}