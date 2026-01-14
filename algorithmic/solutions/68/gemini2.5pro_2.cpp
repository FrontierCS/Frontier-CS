#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

void solve() {
    int n;
    std::cin >> n;

    std::vector<int> candidates(n);
    std::iota(candidates.begin(), candidates.end(), 0);

    while (candidates.size() > 2) {
        int sz = candidates.size();
        int mid = sz / 2;
        
        std::vector<int> group_to_query;
        std::vector<int> group_to_keep;

        for (int i = 0; i < mid; ++i) {
            group_to_query.push_back(candidates[i]);
        }
        for (int i = mid; i < sz; ++i) {
            group_to_keep.push_back(candidates[i]);
        }
        
        std::vector<int> next_candidates = group_to_keep;
        for (int pen : group_to_query) {
            std::cout << "0 " << pen << std::endl;
            int response;
            std::cin >> response;
            if (response == 1) {
                next_candidates.push_back(pen);
            }
        }
        candidates = next_candidates;
    }

    std::cout << "1 " << candidates[0] << " " << candidates[1] << std::endl;
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