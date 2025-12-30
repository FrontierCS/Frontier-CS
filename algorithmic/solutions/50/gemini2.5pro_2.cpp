#include <iostream>
#include <vector>
#include <algorithm>

// Using 1-based indexing for elements and sets as in the problem statement
const int MAXN_P = 400 + 1;
const int MAXM_P = 4000 + 1;

int n, m;
int costs[MAXM_P];
std::vector<int> sets[MAXM_P];      // sets[j] stores elements in set j
std::vector<int> elements[MAXN_P];  // elements[i] stores sets containing element i

bool is_element_covered[MAXN_P];
int num_uncovered_elements;

int uncovered_in_set[MAXM_P];
bool is_set_used[MAXM_P];

int main() {
    // Fast I/O
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> n >> m;

    for (int i = 1; i <= m; ++i) {
        std::cin >> costs[i];
    }

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

    // Initialization
    for (int i = 1; i <= n; ++i) {
        is_element_covered[i] = false;
    }
    num_uncovered_elements = n;
    
    for (int i = 1; i <= m; ++i) {
        uncovered_in_set[i] = sets[i].size();
        is_set_used[i] = false;
    }

    std::vector<int> solution_sets;

    while (num_uncovered_elements > 0) {
        int best_set_id = -1;
        long long best_p = -1, best_q = 1; // Represents the ratio p/q

        for (int j = 1; j <= m; ++j) {
            if (!is_set_used[j] && uncovered_in_set[j] > 0) {
                // Compare costs[j]/uncovered_in_set[j] with best_p/best_q
                // using cross-multiplication to avoid floating point issues.
                if (best_set_id == -1 || (long long)costs[j] * best_q < best_p * uncovered_in_set[j]) {
                    best_p = costs[j];
                    best_q = uncovered_in_set[j];
                    best_set_id = j;
                }
            }
        }

        if (best_set_id == -1) {
            // This should not happen if a full cover is possible as implied by the problem.
            break;
        }

        is_set_used[best_set_id] = true;
        solution_sets.push_back(best_set_id);

        for (int element_id : sets[best_set_id]) {
            if (!is_element_covered[element_id]) {
                is_element_covered[element_id] = true;
                num_uncovered_elements--;
                for (int set_id_containing_element : elements[element_id]) {
                    uncovered_in_set[set_id_containing_element]--;
                }
            }
        }
    }

    std::cout << solution_sets.size() << "\n";
    for (int i = 0; i < solution_sets.size(); ++i) {
        std::cout << solution_sets[i] << (i == solution_sets.size() - 1 ? "" : " ");
    }
    std::cout << "\n";

    return 0;
}