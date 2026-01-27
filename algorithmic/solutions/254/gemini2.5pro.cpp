#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

// Helper function to perform a query
int query(const std::vector<int>& p) {
    std::cout << "?";
    for (int x : p) {
        std::cout << " " << x;
    }
    std::cout << std::endl;
    int winner;
    std::cin >> winner;
    return winner;
}

void solve() {
    int n;
    std::cin >> n;

    // Phase 1: Sort each group of n pepes internally.
    std::vector<std::vector<int>> groups(n);
    for (int i = 0; i < n * n; ++i) {
        groups[i / n].push_back(i + 1);
    }

    std::vector<std::vector<int>> sorted_groups(n);

    for (int i = 0; i < n; ++i) {
        std::vector<int> unsorted = groups[i];
        for (int k = 0; k < n; ++k) {
            std::vector<int> candidates = unsorted;
            while (candidates.size() > 1) {
                std::vector<int> winners;
                // Use a pepe from another group as filler. A simple choice is from group (i+1)%n.
                int filler_group_idx = (i + 1) % n;
                int filler_idx_in_group = 0;

                for (size_t j = 0; j < candidates.size(); j += n - 1) {
                    std::vector<int> race;
                    for (size_t l = 0; l < n - 1 && j + l < candidates.size(); ++l) {
                        race.push_back(candidates[j + l]);
                    }
                    if (race.empty()) continue;

                    int filler = groups[filler_group_idx][filler_idx_in_group];
                    filler_idx_in_group = (filler_idx_in_group + 1) % n;
                    
                    race.push_back(filler);
                    
                    int winner = query(race);
                    if (winner != filler) {
                        winners.push_back(winner);
                    }
                }
                if (winners.empty() && !candidates.empty()) {
                    // This can happen if the filler always wins.
                    // This implies all candidates are slower than the fillers used.
                    // For simplicity, we just take the first candidate.
                    // A more sophisticated strategy could use this information.
                    winners.push_back(candidates[0]);
                }
                candidates = winners;
            }
            int max_val = candidates[0];
            sorted_groups[i].push_back(max_val);
            unsorted.erase(std::remove(unsorted.begin(), unsorted.end(), max_val), unsorted.end());
        }
    }

    // Phase 2: Merge the n sorted lists.
    std::vector<int> final_ranking;
    std::vector<int> ptrs(n, 0);
    // Find a pepe that is likely slow to fill races if a group is exhausted.
    // The last element of any sorted list is a good candidate.
    int slow_pepe = sorted_groups[0].back(); 

    while (final_ranking.size() < n * n - n + 1) {
        std::vector<int> heads;
        for (int i = 0; i < n; ++i) {
            if (ptrs[i] < n) {
                heads.push_back(sorted_groups[i][ptrs[i]]);
            }
        }

        if (heads.empty()) break;
        
        // If there are fewer than n heads because some groups are exhausted,
        // pad the race with the slow pepe.
        while (heads.size() > 1 && heads.size() < (size_t)n) {
            heads.push_back(slow_pepe);
        }

        int winner;
        if (heads.size() == 1) {
            winner = heads[0];
        } else {
            winner = query(heads);
        }
        
        // This check is to ensure we don't add the slow_pepe if it wins
        // when only one real candidate was left.
        bool winner_is_real = false;
        for (int i = 0; i < n; ++i) {
            if (ptrs[i] < n && sorted_groups[i][ptrs[i]] == winner) {
                winner_is_real = true;
                break;
            }
        }
        if (!winner_is_real) {
             for (int h : heads) {
                if(h != slow_pepe) {
                    winner = h;
                    break;
                }
            }
        }

        final_ranking.push_back(winner);

        for (int i = 0; i < n; ++i) {
            if (ptrs[i] < n && sorted_groups[i][ptrs[i]] == winner) {
                ptrs[i]++;
                break;
            }
        }
    }

    std::cout << "!";
    for (int p : final_ranking) {
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