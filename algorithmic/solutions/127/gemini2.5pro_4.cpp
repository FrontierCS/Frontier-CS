#include <iostream>
#include <vector>
#include <utility>
#include <algorithm>
#include <random>
#include <chrono>
#include <map>

// Using a map to cache query results, as the judge is consistent.
std::map<int, std::pair<int, int>> query_cache;

// Function to ask a query, with caching
std::pair<int, int> ask(int i) {
    if (query_cache.count(i)) {
        return query_cache[i];
    }
    std::cout << "? " << i << std::endl;
    int a0, a1;
    std::cin >> a0 >> a1;
    return query_cache[i] = {a0, a1};
}

// Function to give the final answer
void answer(int i) {
    std::cout << "! " << i << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    // Use a high-quality random number generator.
    std::mt19937 rng(std::chrono::steady_clock::now().time_since_epoch().count());
    
    // Phase 1: Random probing to find type 2 prizes and narrow the search range.
    int num_random_probes = std::min(100, n);
    std::vector<int> type2_indices;
    std::vector<bool> probed(n, false);
    
    for (int k = 0; k < num_random_probes; ++k) {
        int i;
        // Generate a random index that has not been probed yet.
        do {
            i = rng() % n;
        } while (probed[i]);
        probed[i] = true;

        auto res = ask(i);
        if (res.first == 0 && res.second == 0) {
            answer(i);
            return 0;
        }
        if (res.first + res.second == 1) {
            type2_indices.push_back(i);
        }
    }

    std::sort(type2_indices.begin(), type2_indices.end());

    int l = 0, r = n - 1;

    if (!type2_indices.empty()) {
        int p_left = type2_indices.front();
        auto res_left = ask(p_left);
        if (res_left.first + res_left.second == 0) {
             answer(p_left);
             return 0;
        }
        if (res_left.first == 1) { // Diamond is to the left
            r = p_left - 1;
        } else { // a1 == 1, diamond is to the right
            l = p_left + 1;
        }

        if (type2_indices.size() > 1) {
            int p_right = type2_indices.back();
            if (p_left != p_right) {
                auto res_right = ask(p_right);
                if (res_right.first + res_right.second == 0) {
                     answer(p_right);
                     return 0;
                }
                if (res_right.first == 1) { // Diamond is to the left
                    r = std::min(r, p_right - 1);
                } else { // a1 == 1, diamond is to the right
                    l = std::max(l, p_right + 1);
                }
            }
        }
    }

    if (l > r) { // Unlikely, but could happen with unlucky probes.
        if (!type2_indices.empty()) answer(type2_indices[0]);
        else answer(0);
        return 0;
    }
    if (l == r) {
        answer(l);
        return 0;
    }

    // Phase 2: Binary search for the jump in `a0`.
    int a0_base;
    if (l == 0) {
        a0_base = 0;
    } else {
        auto res_base = ask(l - 1);
        if (res_base.first + res_base.second == 0) {
            answer(l - 1);
            return 0;
        }
        a0_base = res_base.first;
    }
    
    int ans_idx = l;
    int search_l = l;
    int search_r = r;
    
    while(search_l <= search_r) {
        int mid = search_l + (search_r - search_l) / 2;
        auto res_mid = ask(mid);
        if (res_mid.first == 0 && res_mid.second == 0) {
            answer(mid);
            return 0;
        }

        // Binary search for the first index 'mid' where a0 > a0_base.
        // This marks the position of the diamond.
        if (res_mid.first > a0_base) {
            ans_idx = mid;
            search_r = mid - 1;
        } else {
            search_l = mid + 1;
        }
    }
    
    answer(ans_idx);

    return 0;
}