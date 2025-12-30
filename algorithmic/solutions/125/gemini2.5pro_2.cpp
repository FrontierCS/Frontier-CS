#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

/**
 * @brief Sends a query to the judge and returns the response.
 * 
 * @param x The slice number to toggle.
 * @return int The number of distinct mineral kinds in the device.
 */
int query(int x) {
    std::cout << "? " << x << std::endl;
    int r;
    std::cin >> r;
    if (r == -1) exit(0); // Exit if judge reports an error
    return r;
}

/**
 * @brief Announces a found pair to the judge.
 * 
 * @param a The first slice in the pair.
 * @param b The second slice in the pair.
 */
void answer(int a, int b) {
    std::cout << "! " << a << " " << b << std::endl;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    std::vector<bool> paired(2 * n + 1, false);
    std::vector<int> unmatched_in_device;
    int current_distinct_kinds = 0;

    for (int i = 1; i <= 2 * n; ++i) {
        if (paired[i]) {
            continue;
        }

        int new_distinct_kinds = query(i);

        if (new_distinct_kinds > current_distinct_kinds) {
            // This is a "starter" slice of a new kind.
            unmatched_in_device.push_back(i);
            current_distinct_kinds = new_distinct_kinds;
        } else { 
            // This is a "finisher" slice. Its pair is in unmatched_in_device.
            int base_kinds_for_search = new_distinct_kinds;
            
            // Linearly scan unmatched_in_device to find the pair.
            // Scanning from the end is often a good heuristic.
            for (int j = unmatched_in_device.size() - 1; j >= 0; --j) {
                int u = unmatched_in_device[j];
                int test_kinds = query(u);
                
                if (test_kinds == base_kinds_for_search) {
                    // Found the pair: (i, u).
                    // Removing u did not change the number of kinds, because i has the same kind.
                    answer(i, u);
                    paired[i] = true;
                    paired[u] = true;
                    
                    unmatched_in_device.erase(unmatched_in_device.begin() + j);
                    current_distinct_kinds = test_kinds;
                    break;
                } else {
                    // Not a pair. Put u back into the device to restore the state for the next check.
                    query(u);
                }
            }
        }
    }

    return 0;
}