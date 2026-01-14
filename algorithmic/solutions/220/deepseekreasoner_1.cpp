#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<vector<int>> state(n);
    for (int i = 0; i < n; ++i) {
        state[i].resize(n);
        for (int j = 0; j < n; ++j) {
            cin >> state[i][j];
        }
    }

    vector<vector<int>> ops;

    // Process numbers from n down to 1
    for (int num = n; num >= 1; --num) {
        int player_idx = num - 1; // 0-indexed
        while (true) {
            // Count how many cards of number 'num' the player has
            int cnt = 0;
            for (int card : state[player_idx]) {
                if (card == num) cnt++;
            }
            if (cnt == n) break; // player already has all his cards

            // Safety stop: if we already used the maximum allowed operations
            if (ops.size() >= n * n - n) break;

            vector<int> pass(n);
            for (int j = 0; j < n; ++j) {
                if (j == player_idx) {
                    // Player 'num' must pass a card that is not 'num'
                    int chosen = -1;
                    for (int card : state[j]) {
                        if (card != num) {
                            chosen = card;
                            break;
                        }
                    }
                    if (chosen == -1) chosen = state[j][0]; // fallback (should not happen)
                    pass[j] = chosen;
                } else if (j < player_idx) {
                    // Player with smaller index: pass a card of number 'num' if possible
                    int chosen = -1;
                    for (int card : state[j]) {
                        if (card == num) {
                            chosen = card;
                            break;
                        }
                    }
                    if (chosen == -1) chosen = state[j][0];
                    pass[j] = chosen;
                } else {
                    // Player with larger index: pass a card that is not his own number if possible
                    int own_num = j + 1;
                    int chosen = -1;
                    for (int card : state[j]) {
                        if (card != own_num) {
                            chosen = card;
                            break;
                        }
                    }
                    if (chosen == -1) chosen = state[j][0];
                    pass[j] = chosen;
                }
            }

            // Apply the operation
            vector<int> received(n);
            for (int j = 0; j < n; ++j) {
                received[(j + 1) % n] = pass[j];
            }
            for (int j = 0; j < n; ++j) {
                // Remove pass[j] from state[j]
                auto it = find(state[j].begin(), state[j].end(), pass[j]);
                state[j].erase(it);
                // Add received[j] to state[j]
                state[j].push_back(received[j]);
            }

            ops.push_back(pass);
        }
    }

    // Output
    cout << ops.size() << "\n";
    for (const auto& op : ops) {
        for (int j = 0; j < n; ++j) {
            cout << op[j] << " \n"[j == n-1];
        }
    }

    return 0;
}