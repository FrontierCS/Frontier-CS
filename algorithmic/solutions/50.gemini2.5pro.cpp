#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n, m;
    std::cin >> n >> m;

    std::vector<int> costs(m);
    for (int i = 0; i < m; ++i) {
        std::cin >> costs[i];
    }

    std::vector<std::vector<int>> sets_containing_element(n);
    std::vector<std::vector<int>> elements_in_set(m);
    
    for (int i = 0; i < n; ++i) {
        int k;
        std::cin >> k;
        sets_containing_element[i].reserve(k);
        for (int j = 0; j < k; ++j) {
            int set_id;
            std::cin >> set_id;
            --set_id; // 0-based indexing
            sets_containing_element[i].push_back(set_id);
            elements_in_set[set_id].push_back(i);
        }
    }

    std::vector<int> uncovered_elements_in_set(m);
    for (int i = 0; i < m; ++i) {
        uncovered_elements_in_set[i] = elements_in_set[i].size();
    }

    std::vector<bool> is_element_covered(n, false);
    int num_uncovered_elements = n;
    
    std::vector<bool> is_set_chosen(m, false);
    std::vector<int> solution_sets;
    solution_sets.reserve(n);

    while (num_uncovered_elements > 0) {
        int best_set_idx = -1;
        long long best_num = -1;
        long long best_den = 1;

        for (int i = 0; i < m; ++i) {
            if (is_set_chosen[i] || uncovered_elements_in_set[i] == 0) {
                continue;
            }

            if (best_set_idx == -1 || (long long)costs[i] * best_den < best_num * uncovered_elements_in_set[i]) {
                best_set_idx = i;
                best_num = costs[i];
                best_den = uncovered_elements_in_set[i];
            }
        }
        
        if (best_set_idx == -1) {
            // This should not happen if a valid cover always exists
            break;
        }

        is_set_chosen[best_set_idx] = true;
        solution_sets.push_back(best_set_idx + 1); // Output is 1-based

        for (int element_idx : elements_in_set[best_set_idx]) {
            if (!is_element_covered[element_idx]) {
                is_element_covered[element_idx] = true;
                num_uncovered_elements--;
                
                for (int set_idx : sets_containing_element[element_idx]) {
                    uncovered_elements_in_set[set_idx]--;
                }
            }
        }
    }

    std::cout << solution_sets.size() << "\n";
    for (size_t i = 0; i < solution_sets.size(); ++i) {
        std::cout << solution_sets[i] << (i == solution_sets.size() - 1 ? "" : " ");
    }
    std::cout << "\n";

    return 0;
}