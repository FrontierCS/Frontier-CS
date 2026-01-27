#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <list>

void solve() {
    int n;
    std::cin >> n;

    if (n == 0) return;

    int n_sq = n * n;
    
    std::vector<std::list<int>> groups_remaining(n);
    std::vector<int> group_of_pepe(n_sq + 1);

    int current_pepe = 1;
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            groups_remaining[i].push_back(current_pepe);
            group_of_pepe[current_pepe] = i;
            current_pepe++;
        }
    }

    auto make_query = [&](const std::vector<int>& racers) {
        std::cout << "?";
        for (int pepe : racers) {
            std::cout << " " << pepe;
        }
        std::cout << std::endl;
        int winner;
        std::cin >> winner;
        return winner;
    };

    std::vector<int> candidates(n);
    std::vector<int> pepes_to_race(n);
    for (int i = 0; i < n; ++i) {
        std::copy(groups_remaining[i].begin(), groups_remaining[i].end(), pepes_to_race.begin());
        int winner = make_query(pepes_to_race);
        candidates[i] = winner;
        groups_remaining[i].remove(winner);
    }

    std::vector<int> ans;
    ans.reserve(n_sq - n + 1);

    std::vector<bool> in_ans(n_sq + 1, false);
    std::vector<bool> is_candidate(n_sq + 1, false);
    for(int c : candidates) {
        if (c > 0) is_candidate[c] = true;
    }

    while (ans.size() < n_sq - n + 1) {
        std::vector<int> current_racers;
        for (int c : candidates) {
            if (c > 0) {
                current_racers.push_back(c);
            }
        }

        if (current_racers.empty()) {
            break;
        }
        
        if (current_racers.size() < n) {
            std::vector<bool> in_current_race(n_sq + 1, false);
            for(int p : current_racers) in_current_race[p] = true;
            
            bool filled = false;
            for(int i = 0; i < n && !filled; ++i) {
                for(int p : groups_remaining[i]) {
                    if (!in_current_race[p]) {
                        current_racers.push_back(p);
                        in_current_race[p] = true;
                        if(current_racers.size() == n) {
                            filled = true;
                            break;
                        }
                    }
                }
            }
        }

        int winner = make_query(current_racers);

        ans.push_back(winner);
        in_ans[winner] = true;
        is_candidate[winner] = false;

        int winner_group_idx = group_of_pepe[winner];
        
        for(int i=0; i<n; ++i) {
            if(candidates[i] == winner) {
                if (groups_remaining[winner_group_idx].empty()) {
                    candidates[i] = 0;
                } else {
                    if (groups_remaining[winner_group_idx].size() == 1) {
                        int new_candidate = groups_remaining[winner_group_idx].front();
                        groups_remaining[winner_group_idx].pop_front();
                        candidates[i] = new_candidate;
                        is_candidate[new_candidate] = true;
                    } else {
                        std::vector<int> promotion_racers;
                        for(int p : groups_remaining[winner_group_idx]) {
                            promotion_racers.push_back(p);
                        }

                        if (promotion_racers.size() < n) {
                           std::vector<bool> in_promo_race(n_sq + 1, false);
                           for(int p : promotion_racers) in_promo_race[p] = true;
                            
                           bool filled = false;
                           for(int j = 0; j < n && !filled; ++j) {
                                for(int p : groups_remaining[j]) {
                                    if (!in_promo_race[p]) {
                                        promotion_racers.push_back(p);
                                        in_promo_race[p] = true;
                                        if (promotion_racers.size() == n) {
                                            filled = true;
                                            break;
                                        }
                                    }
                                }
                           }
                        }
                        
                        int new_candidate = make_query(promotion_racers);
                        groups_remaining[winner_group_idx].remove(new_candidate);
                        candidates[i] = new_candidate;
                        is_candidate[new_candidate] = true;
                    }
                }
                break;
            }
        }
    }

    std::cout << "!";
    for (size_t i = 0; i < ans.size(); ++i) {
        std::cout << " " << ans[i];
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