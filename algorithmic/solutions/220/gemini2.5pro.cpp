#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

int n;
vector<vector<int>> adj;
vector<bool> visited_players;
vector<int> card_val_match;

// Finds an augmenting path for a perfect matching in a bipartite graph
bool find_path(int p) {
    if (visited_players[p]) {
        return false;
    }
    visited_players[p] = true;
    for (int v_idx : adj[p]) {
        if (card_val_match[v_idx] < 0 || find_path(card_val_match[v_idx])) {
            card_val_match[v_idx] = p;
            return true;
        }
    }
    return false;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n;
    vector<vector<int>> initial_counts(n, vector<int>(n + 1, 0));
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            int card;
            cin >> card;
            initial_counts[i][card]++;
        }
    }

    vector<vector<int>> operations;

    // Stage 1: The Matching Operation
    // Goal: transition to a state where player i has all cards of value (i+1 % n) + 1.
    // To do this, the set of passed cards must be {1, 2, ..., n}.
    // We find a perfect matching between players and card values {1, ..., n}.
    
    adj.assign(n, vector<int>());
    for (int p = 0; p < n; ++p) { // player p (0-indexed)
        for (int v = 1; v <= n; ++v) { // card value v
            if (initial_counts[p][v] > 0) {
                adj[p].push_back(v - 1); // map card value v to index v-1
            }
        }
    }
    
    card_val_match.assign(n, -1);
    for (int p = 0; p < n; ++p) {
        visited_players.assign(n, false);
        find_path(p);
    }
    
    vector<int> op1(n);
    vector<int> player_match(n);
    for (int v_idx = 0; v_idx < n; ++v_idx) {
        player_match[card_val_match[v_idx]] = v_idx;
    }
    for (int p = 0; p < n; ++p) {
        op1[p] = player_match[p] + 1;
    }
    operations.push_back(op1);
    
    // After this operation, player i is guaranteed to have all cards of value (i % n) + 1.
    // This is state T_1.

    // Stage 2: Rotation Operations
    // From T_k to T_{k-1}, player i passes (i+k-1 % n) + 1.
    // We start from T_1 and want to reach T_0 (solved state). This takes 1 rotation.
    // player i passes (i+1-1 % n) + 1 = (i % n) + 1.
    
    // Wait, let's trace: after op1, player i gets op1[(i-1+n)%n]. The set of cards passed
    // op1 is {1,...,n}. So player i might get any value.
    // The state achieved is where player i has all cards of value op1[(i-1+n)%n].
    // Let's call this permutation sigma. player i has cards sigma(i).
    // We need n-1 rotations to bring card sigma(i) to player sigma(i).
    
    // A simpler logic: After the first matching step where passed cards are {1..n},
    // player i gets card op1[(i-1+n)%n]. Now player i has n cards of this value.
    // This is a permuted solid state. Let's call it T_sigma.
    // To solve it, we need to route cards.
    // player i has cards v = op1[(i-1+n)%n]. It needs to send them to player v.
    // This can be done in n-1 steps.
    // At step k (1..n-1), player i, who has cards v, passes v.
    // The card v will reach its destination.
    
    vector<int> current_card_values = op1;
    for(int p=0; p<n; ++p) {
        // Player p passed current_card_values[p].
        // Player p received current_card_values[(p-1+n)%n].
        // So after op1, player p has n cards of value current_card_values[(p-1+n)%n].
    }

    vector<int> card_at_player(n);
    for(int p=0; p<n; ++p) {
        card_at_player[p] = current_card_values[(p-1+n)%n];
    }
    
    for (int k = 0; k < n-1; ++k) {
        vector<int> next_op(n);
        for (int p = 0; p < n; ++p) {
            next_op[p] = card_at_player[p];
        }
        operations.push_back(next_op);
        
        vector<int> next_card_at_player(n);
        for(int p=0; p<n; ++p) {
            next_card_at_player[p] = card_at_player[(p-1+n)%n];
        }
        card_at_player = next_card_at_player;
    }


    cout << operations.size() << "\n";
    for (const auto& op : operations) {
        for (int i = 0; i < n; ++i) {
            cout << op[i] << (i == n - 1 ? "" : " ");
        }
        cout << "\n";
    }

    return 0;
}