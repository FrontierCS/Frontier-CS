#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <limits>

void fast_io() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);
}

int main() {
    fast_io();

    int n, m;
    std::cin >> n >> m;

    std::vector<long long> cost(m + 1);
    for (int i = 1; i <= m; ++i) {
        std::cin >> cost[i];
    }

    std::vector<std::vector<int>> sets(m + 1);
    std::vector<std::vector<int>> elements(n + 1);

    for (int i = 1; i <= n; ++i) {
        int k;
        std::cin >> k;
        for (int j = 0; j < k; ++j) {
            int set_id;
            std::cin >> set_id;
            sets[set_id].push_back(i);
            elements[i].push_back(set_id);
        }
    }

    // --- Greedy Algorithm for Set Cover ---
    std::vector<bool> is_element_covered(n + 1, false);
    int num_uncovered_elements = n;

    std::vector<int> uncovered_elements_in_set(m + 1);
    for (int i = 1; i <= m; ++i) {
        uncovered_elements_in_set[i] = sets[i].size();
    }

    std::vector<bool> is_set_chosen(m + 1, false);
    std::vector<int> greedy_solution_sets;

    while (num_uncovered_elements > 0) {
        int best_set_id = -1;
        long double min_ratio = std::numeric_limits<long double>::max();

        for (int i = 1; i <= m; ++i) {
            if (!is_set_chosen[i] && uncovered_elements_in_set[i] > 0) {
                long double ratio = static_cast<long double>(cost[i]) / uncovered_elements_in_set[i];
                if (ratio < min_ratio) {
                    min_ratio = ratio;
                    best_set_id = i;
                }
            }
        }

        if (best_set_id == -1) {
            break; 
        }

        greedy_solution_sets.push_back(best_set_id);
        is_set_chosen[best_set_id] = true;

        for (int element_id : sets[best_set_id]) {
            if (!is_element_covered[element_id]) {
                is_element_covered[element_id] = true;
                num_uncovered_elements--;
                for (int set_id_to_update : elements[element_id]) {
                    uncovered_elements_in_set[set_id_to_update]--;
                }
            }
        }
    }

    // --- Post-processing: Redundancy Removal ---
    std::vector<int> cover_count(n + 1, 0);
    for (int set_id : greedy_solution_sets) {
        for (int element_id : sets[set_id]) {
            cover_count[element_id]++;
        }
    }

    std::vector<int> sorted_solution = greedy_solution_sets;
    std::sort(sorted_solution.begin(), sorted_solution.end(), [&](int a, int b) {
        return cost[a] > cost[b];
    });

    std::vector<bool> is_set_in_final_solution(m + 1, false);
    for (int set_id : greedy_solution_sets) {
        is_set_in_final_solution[set_id] = true;
    }

    for (int set_id : sorted_solution) {
        bool is_redundant = true;
        for (int element_id : sets[set_id]) {
            if (cover_count[element_id] < 2) {
                is_redundant = false;
                break;
            }
        }

        if (is_redundant) {
            is_set_in_final_solution[set_id] = false;
            for (int element_id : sets[set_id]) {
                cover_count[element_id]--;
            }
        }
    }

    std::vector<int> final_solution_sets;
    for (int i = 1; i <= m; ++i) {
        if (is_set_in_final_solution[i]) {
            final_solution_sets.push_back(i);
        }
    }
    
    std::sort(final_solution_sets.begin(), final_solution_sets.end());

    std::cout << final_solution_sets.size() << "\n";
    for (size_t i = 0; i < final_solution_sets.size(); ++i) {
        std::cout << final_solution_sets[i] << (i == final_solution_sets.size() - 1 ? "" : " ");
    }
    std::cout << "\n";

    return 0;
}