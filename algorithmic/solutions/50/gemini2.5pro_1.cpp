#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

void solve() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n, m;
    std::cin >> n >> m;

    std::vector<long long> costs(m + 1);
    for (int i = 1; i <= m; ++i) {
        std::cin >> costs[i];
    }

    std::vector<std::vector<int>> elements_in_set(m + 1);
    std::vector<std::vector<int>> sets_containing_element(n + 1);
    for (int i = 1; i <= n; ++i) {
        int k;
        std::cin >> k;
        for (int j = 0; j < k; ++j) {
            int set_id;
            std::cin >> set_id;
            elements_in_set[set_id].push_back(i);
            sets_containing_element[i].push_back(set_id);
        }
    }

    std::vector<bool> is_element_covered(n + 1, false);
    int uncovered_elements_count = n;
    
    std::vector<int> uncovered_in_set(m + 1);
    for (int i = 1; i <= m; ++i) {
        uncovered_in_set[i] = elements_in_set[i].size();
    }
    
    std::vector<bool> is_set_chosen(m + 1, false);
    std::vector<int> solution_sets;

    // Phase 1: Greedily pick the best zero-cost sets
    while (true) {
        int best_zero_cost_set = -1;
        int max_uncovered = 0;
        
        for (int i = 1; i <= m; ++i) {
            if (costs[i] == 0 && !is_set_chosen[i] && uncovered_in_set[i] > max_uncovered) {
                max_uncovered = uncovered_in_set[i];
                best_zero_cost_set = i;
            }
        }
        
        if (max_uncovered == 0) {
            break;
        }
        
        int s_id = best_zero_cost_set;
        solution_sets.push_back(s_id);
        is_set_chosen[s_id] = true;
        
        std::vector<int> newly_covered;
        for (int element : elements_in_set[s_id]) {
            if (!is_element_covered[element]) {
                is_element_covered[element] = true;
                newly_covered.push_back(element);
            }
        }
        
        uncovered_elements_count -= newly_covered.size();
        for (int element : newly_covered) {
            for (int set_idx : sets_containing_element[element]) {
                uncovered_in_set[set_idx]--;
            }
        }
    }

    // Phase 2: Greedily pick positive-cost sets
    while (uncovered_elements_count > 0) {
        int best_set_idx = -1;
        double max_ratio = -1.0;

        for (int i = 1; i <= m; ++i) {
            if (!is_set_chosen[i] && uncovered_in_set[i] > 0) {
                double current_ratio = static_cast<double>(uncovered_in_set[i]) / costs[i];
                if (current_ratio > max_ratio) {
                    max_ratio = current_ratio;
                    best_set_idx = i;
                }
            }
        }

        if (best_set_idx == -1) {
            break;
        }

        solution_sets.push_back(best_set_idx);
        is_set_chosen[best_set_idx] = true;

        std::vector<int> newly_covered;
        for (int element : elements_in_set[best_set_idx]) {
            if (!is_element_covered[element]) {
                is_element_covered[element] = true;
                newly_covered.push_back(element);
            }
        }
        
        uncovered_elements_count -= newly_covered.size();
        for (int element : newly_covered) {
            for (int set_idx : sets_containing_element[element]) {
                uncovered_in_set[set_idx]--;
            }
        }
    }

    std::sort(solution_sets.begin(), solution_sets.end());

    std::cout << solution_sets.size() << "\n";
    for (size_t i = 0; i < solution_sets.size(); ++i) {
        std::cout << solution_sets[i] << (i == solution_sets.size() - 1 ? "" : " ");
    }
    std::cout << "\n";
}

int main() {
    solve();
    return 0;
}