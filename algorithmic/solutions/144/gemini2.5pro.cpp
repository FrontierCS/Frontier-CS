#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <map>

// Function to make a query to the interactor
std::pair<int, int> do_query(const std::vector<int>& indices) {
    std::cout << "0 " << indices.size();
    for (int idx : indices) {
        std::cout << " " << idx;
    }
    std::cout << std::endl;
    int m1, m2;
    std::cin >> m1 >> m2;
    return {m1, m2};
}

// Function to find the median of values at three indices: a, b, c
// This costs 2 queries
int get_median_of_three(int n, int a, int b, int c) {
    int d1 = -1, d2 = -1;
    for (int i = 1; i <= n; ++i) {
        if (i != a && i != b && i != c) {
            if (d1 == -1) d1 = i;
            else {
                d2 = i;
                break;
            }
        }
    }

    auto res1 = do_query({a, b, c, d1});
    auto res2 = do_query({a, b, c, d2});

    if (res1.first == res2.first || res1.first == res2.second) {
        return res1.first;
    }
    return res1.second;
}

// Comparison function to check if p[a] > p[b]
// Costs 4 queries by finding medians with two helper indices
bool is_greater(int n, int a, int b) {
    int c = -1, d = -1;
    for (int i = 1; i <= n; ++i) {
        if (i != a && i != b) {
            if (c == -1) c = i;
            else {
                d = i;
                break;
            }
        }
    }
    int med_a = get_median_of_three(n, a, c, d);
    int med_b = get_median_of_three(n, b, c, d);
    return med_a > med_b;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    // Phase 1: Find min_idx and max_idx
    int h1 = 1, h2 = 2;
    int min_idx_rest = 3, max_idx_rest = 3;
    
    int med3 = get_median_of_three(n, 3, h1, h2);
    int min_med = med3, max_med = med3;

    for (int i = 4; i <= n; ++i) {
        int med_i = get_median_of_three(n, i, h1, h2);
        if (med_i < min_med) {
            min_med = med_i;
            min_idx_rest = i;
        }
        if (med_i > max_med) {
            max_med = med_i;
            max_idx_rest = i;
        }
    }

    int min_idx = min_idx_rest;
    if (is_greater(n, min_idx, h1)) min_idx = h1;
    if (is_greater(n, min_idx, h2)) min_idx = h2;

    int max_idx = max_idx_rest;
    if (is_greater(n, h1, max_idx)) max_idx = h1;
    if (is_greater(n, h2, max_idx)) max_idx = h2;
    
    // Phase 2: Find all other values
    std::map<int, int> p_val;
    p_val[min_idx] = 1;
    p_val[max_idx] = n;
    
    std::vector<int> remaining_indices;
    for(int i = 1; i <= n; ++i) {
        if (i != min_idx && i != max_idx) {
            remaining_indices.push_back(i);
        }
    }

    for (int idx : remaining_indices) {
        int other1 = -1, other2 = -1;
        for (int k = 1; k <= n; ++k) {
            if (k != idx && k != min_idx && k != max_idx) {
                if (other1 == -1) other1 = k;
                else {
                    other2 = k;
                    break;
                }
            }
        }
        
        auto res1 = do_query({idx, min_idx, max_idx, other1});
        auto res2 = do_query({idx, min_idx, max_idx, other2});

        if (res1.first == res2.first || res1.first == res2.second) {
            p_val[idx] = res1.first;
        } else {
            p_val[idx] = res1.second;
        }
    }

    int med1_idx = -1, med2_idx = -1;
    for (auto const& [idx, val] : p_val) {
        if (val == n / 2) {
            med1_idx = idx;
        }
        if (val == n / 2 + 1) {
            med2_idx = idx;
        }
    }
    
    std::cout << "1 " << med1_idx << " " << med2_idx << std::endl;

    return 0;
}