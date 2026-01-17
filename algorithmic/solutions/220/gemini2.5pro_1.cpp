#include <iostream>
#include <vector>
#include <numeric>
#include <array>

using namespace std;

// Finds the smallest card value c in player p's hand such that c != v_except.
// If no such card exists, it returns v_except.
int find_smallest_except(int p, int v_except, int n, const vector<array<int, 101>>& counts) {
    for (int c = 1; c <= n; ++c) {
        if (c != v_except && counts[p][c] > 0) {
            return c;
        }
    }
    return v_except; // Must pass v_except as it's the only option
}

// Finds the smallest card value c in player p's hand.
int find_smallest(int p, int n, const vector<array<int, 101>>& counts) {
    for (int c = 1; c <= n; ++c) {
        if (counts[p][c] > 0) {
            return c;
        }
    }
    return -1; // Should not happen, as a player always has cards.
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;

    vector<array<int, 101>> counts(n + 1);
    for (int i = 1; i <= n; ++i) {
        counts[i].fill(0);
        for (int j = 0; j < n; ++j) {
            int card;
            cin >> card;
            counts[i][card]++;
        }
    }

    vector<vector<int>> operations;

    // We perform n phases, one for each card value v from 1 to n.
    // Each phase consists of n-1 operations.
    for (int v = 1; v <= n; ++v) {
        // n-1 operations are enough for any card to travel to any player.
        for (int k = 0; k < n - 1; ++k) {
            vector<int> current_passes(n + 1);
            for (int i = 1; i <= n; ++i) {
                if (i == v) {
                    // Player v is the destination for cards v.
                    // It should pass any card other than v if possible.
                    current_passes[i] = find_smallest_except(i, v, n, counts);
                } else {
                    // Other players i != v should prioritize passing card v.
                    if (counts[i][v] > 0) {
                        current_passes[i] = v;
                    } else {
                        // If no card v, pass the smallest available card.
                        current_passes[i] = find_smallest(i, n, counts);
                    }
                }
            }
            operations.push_back(current_passes);

            // Update card counts based on the passes.
            vector<array<int, 101>> next_counts = counts;
            for (int i = 1; i <= n; ++i) {
                int card_passed = current_passes[i];
                next_counts[i][card_passed]--;
                
                int prev_player = (i == 1) ? n : i - 1;
                int card_received = current_passes[prev_player];
                next_counts[i][card_received]++;
            }
            counts = next_counts;
        }
    }

    cout << operations.size() << "\n";
    for (const auto& op : operations) {
        for (int i = 1; i <= n; ++i) {
            cout << op[i] << (i == n ? "" : " ");
        }
        cout << "\n";
    }

    return 0;
}