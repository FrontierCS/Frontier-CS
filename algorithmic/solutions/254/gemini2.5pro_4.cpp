#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <cmath>

int query(const std::vector<int>& pepes) {
    std::cout << "?";
    for (int p : pepes) {
        std::cout << " " << p;
    }
    std::cout << std::endl;
    int winner;
    std::cin >> winner;
    return winner;
}

int find_max(const std::vector<int>& all_candidates, int n) {
    std::vector<int> current_contenders = all_candidates;

    while (current_contenders.size() > 1) {
        std::vector<int> winners;
        std::vector<int> losers_from_full_groups;

        size_t num_full_groups = current_contenders.size() / n;
        for (size_t i = 0; i < num_full_groups; ++i) {
            std::vector<int> race_group;
            for (size_t j = 0; j < n; ++j) {
                race_group.push_back(current_contenders[i * n + j]);
            }
            int winner = query(race_group);
            winners.push_back(winner);
            for (int p : race_group) {
                if (p != winner) {
                    losers_from_full_groups.push_back(p);
                }
            }
        }

        size_t remaining_size = current_contenders.size() % n;
        if (remaining_size > 0) {
            std::vector<int> race_group;
            for (size_t i = num_full_groups * n; i < current_contenders.size(); ++i) {
                race_group.push_back(current_contenders[i]);
            }
            
            int needed_fillers = n - race_group.size();
            
            if (!losers_from_full_groups.empty()) {
                for (int i = 0; i < needed_fillers; ++i) {
                    race_group.push_back(losers_from_full_groups[i]);
                }
            } else {
                // This case happens when current_contenders.size() < n.
                // Fillers must be from all_candidates but not in current_contenders.
                std::vector<bool> is_contender(n * n + 1, false);
                for (int p : current_contenders) {
                    is_contender[p] = true;
                }

                for (int p : all_candidates) {
                    if (!is_contender[p]) {
                        race_group.push_back(p);
                        if (race_group.size() == n) break;
                    }
                }
            }
            winners.push_back(query(race_group));
        }
        current_contenders = winners;
    }
    return current_contenders[0];
}

void solve() {
    int n;
    std::cin >> n;

    std::vector<int> remaining_pepes(n * n);
    std::iota(remaining_pepes.begin(), remaining_pepes.end(), 1);

    std::vector<int> sorted_pepes;
    for (int i = 0; i < n * n - n + 1; ++i) {
        int best = find_max(remaining_pepes, n);
        sorted_pepes.push_back(best);
        remaining_pepes.erase(std::remove(remaining_pepes.begin(), remaining_pepes.end(), best), remaining_pepes.end());
    }

    std::cout << "!";
    for (int p : sorted_pepes) {
        std::cout << " " << p;
    }
    std::cout << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
    int t;
    std::cin >> t;
    while (t--) {
        solve();
    }
    return 0;
}