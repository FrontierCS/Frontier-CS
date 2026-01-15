#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <list>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    std::vector<std::list<int>> hands(n + 1);
    for (int i = 1; i <= n; ++i) {
        for (int j = 0; j < n; ++j) {
            int card;
            std::cin >> card;
            hands[i].push_back(card);
        }
    }

    std::vector<std::vector<int>> operations;

    for (int r = 0; r < n - 1; ++r) {
        for (int k = 0; k < n; ++k) {
            std::vector<int> target_values(n + 1);
            for (int p = 1; p <= n; ++p) {
                target_values[p] = (p + k - 1) % n + 1;
            }

            std::vector<std::vector<int>> players_with_val(n + 1);
            for (int p = 1; p <= n; ++p) {
                for (int card : hands[p]) {
                    players_with_val[card].push_back(p);
                }
            }

            std::vector<int> pass_op(n + 1);
            std::vector<int> val_matched_to_player(n + 1, 0);
            std::vector<bool> player_is_matched(n + 1, false);

            for (int p = 1; p <= n; ++p) {
                int val_to_pass = target_values[p];
                for (int player_candidate : players_with_val[val_to_pass]) {
                    if (!player_is_matched[player_candidate]) {
                        val_matched_to_player[val_to_pass] = player_candidate;
                        player_is_matched[player_candidate] = true;
                        break;
                    }
                }
            }

            for (int v = 1; v <= n; ++v) {
                pass_op[val_matched_to_player[v]] = v;
            }
            operations.push_back(pass_op);

            std::vector<std::list<int>> next_hands(n + 1);
            for (int p = 1; p <= n; ++p) {
                bool passed = false;
                for (int card : hands[p]) {
                    if (!passed && card == pass_op[p]) {
                        passed = true;
                    } else {
                        next_hands[p].push_back(card);
                    }
                }
            }
            for (int p = 1; p <= n; ++p) {
                int prev_p = (p == 1) ? n : p - 1;
                next_hands[p].push_back(pass_op[prev_p]);
            }
            hands = next_hands;
        }
    }
    
    std::cout << operations.size() << "\n";
    for (const auto& op : operations) {
        for (int i = 1; i <= n; ++i) {
            std::cout << op[i] << (i == n ? "" : " ");
        }
        std::cout << "\n";
    }

    return 0;
}