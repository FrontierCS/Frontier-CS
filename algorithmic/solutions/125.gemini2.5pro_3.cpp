#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

// Function to send a query and receive a response
int query(int x) {
    std::cout << "? " << x << std::endl;
    int r;
    std::cin >> r;
    return r;
}

// Function to output an answer
void answer(int a, int b) {
    std::cout << "! " << a << " " << b << std::endl;
}

int main() {
    // Fast I/O
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    std::vector<bool> paired(2 * n + 1, false);
    std::vector<int> unmatched_in_device; // Simulates a stack
    int current_distinct_kinds = 0;
    int pairs_found = 0;

    for (int i = 1; i <= 2 * n; ++i) {
        if (paired[i]) {
            continue;
        }

        // Toggle slice i's presence in the device
        int r = query(i);

        if (r > current_distinct_kinds) {
            // i's mate is not in the device. Add i to the set of unmatched slices.
            unmatched_in_device.push_back(i);
            current_distinct_kinds = r;
        } else {
            // r == current_distinct_kinds. i's mate is in unmatched_in_device.
            // Let's find it.
            
            // The number of distinct kinds among the slices in unmatched_in_device is `current_distinct_kinds`.
            // After inserting i, the device contains {i} U unmatched_in_device, and the number of
            // distinct kinds is still `current_distinct_kinds`. This is our baseline for checks.
            int k_before_search = current_distinct_kinds;

            std::vector<int> temp_removed;
            
            while (!unmatched_in_device.empty()) {
                int j = unmatched_in_device.back();
                unmatched_in_device.pop_back();

                // Remove j to test if it's the mate of i
                int r_test = query(j);
                
                // State before this query: device had {i} U (unmatched_in_device_at_this_point U {j} U temp_removed)
                // Kinds = k_before_search
                // State after query: device has {i} U (unmatched_in_device_at_this_point U temp_removed)
                // This remaining set is S_old \ {j}.
                // If j is the mate of i, then i becomes a new, unpaired kind among the remaining slices.
                // Kinds = |S_old \ {j}| + 1 = (k_before_search - 1) + 1 = k_before_search.
                // If j is not the mate of i, i's mate is still in S_old \ {j}.
                // Kinds = |S_old \ {j}| = k_before_search - 1.
                
                if (r_test == k_before_search) {
                    // j is the mate of i
                    answer(i, j);
                    pairs_found++;
                    paired[i] = true;
                    paired[j] = true;

                    // i is in the device, j is not. Remove i.
                    // The returned value updates current_distinct_kinds for the remaining items.
                    current_distinct_kinds = query(i);

                    // Restore the other unmatched items that were temporarily removed
                    for (int x : temp_removed) {
                        current_distinct_kinds = query(x);
                        unmatched_in_device.push_back(x);
                    }
                    
                    break; 
                } else {
                    // j is not the mate, keep it aside temporarily
                    temp_removed.push_back(j);
                }
            }
        }

        if (pairs_found == n) {
            break;
        }
    }

    return 0;
}