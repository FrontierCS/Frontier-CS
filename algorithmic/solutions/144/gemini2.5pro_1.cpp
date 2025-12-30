#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <random>

// Function to make a query and read the response
std::pair<int, int> do_query(const std::vector<int>& indices) {
    std::cout << "0 " << indices.size();
    for (int index : indices) {
        std::cout << " " << index;
    }
    std::cout << std::endl;
    int m1, m2;
    std::cin >> m1 >> m2;
    if (m1 > m2) std::swap(m1, m2);
    return {m1, m2};
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    std::vector<int> all_indices(n);
    std::iota(all_indices.begin(), all_indices.end(), 1);

    // Query all elements to find the global median values
    auto global_medians = do_query(all_indices);

    int ans1 = -1, ans2 = -1;

    std::mt19937 rng(1337); // Fixed seed for deterministic behavior

    for (int i = 1; i <= n; ++i) {
        for (int j = i + 1; j <= n; ++j) {
            bool is_candidate_pair = true;
            
            std::vector<int> others;
            for (int k = 1; k <= n; ++k) {
                if (k != i && k != j) {
                    others.push_back(k);
                }
            }

            int num_checks = std::min((int)others.size() / 2, 10);

            for (int check = 0; check < num_checks; ++check) {
                std::shuffle(others.begin(), others.end(), rng);
                std::vector<int> query_indices = {i, j, others[0], others[1]};
                auto medians = do_query(query_indices);
                if (medians != global_medians) {
                    is_candidate_pair = false;
                    break;
                }
            }
            
            if (is_candidate_pair) {
                ans1 = i;
                ans2 = j;
                break;
            }
        }
        if (ans1 != -1) {
            break;
        }
    }

    std::cout << "1 " << ans1 << " " << ans2 << std::endl;

    return 0;
}