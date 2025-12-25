#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

// Function to perform a query
int query(int x) {
    std::cout << "? " << x << std::endl;
    int r;
    std::cin >> r;
    // In case of error from judge
    if (r == -1) exit(0);
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

    // Slices that are in the device and do not have a known pair yet.
    // Invariant: all slices in this vector are currently in the device.
    std::vector<int> active_slices;
    // The number of distinct kinds of minerals in the device.
    // Invariant: this matches the count for the set of slices in active_slices.
    int current_distinct_kinds = 0;
    
    // To keep track of which slices have been paired.
    std::vector<bool> paired(2 * n + 1, false);
    int pairs_found = 0;

    // Process slices one by one
    for (int i = 1; i <= 2 * n; ++i) {
        if (paired[i]) {
            continue;
        }

        // Toggle slice i's presence in the device.
        int new_distinct_kinds = query(i);

        if (new_distinct_kinds > current_distinct_kinds) {
            // This is a slice of a new, unseen kind.
            // Add it to our set of active slices.
            active_slices.push_back(i);
            current_distinct_kinds = new_distinct_kinds;
        } else {
            // The number of distinct kinds did not increase.
            // This means slice i must form a pair with one of the slices already in the device.
            // The device now contains all previous active_slices and i.
            // The number of distinct kinds is `current_distinct_kinds`.
            
            int partner = -1;
            
            // We need to find which slice in `active_slices` is the partner.
            // We can do this by removing them one by one and checking the count.
            for (int s : active_slices) {
                // Temporarily remove s from the device
                int distinct_after_removal = query(s);

                // If s is the partner of i, the number of distinct kinds will remain `current_distinct_kinds`.
                // Otherwise, it will decrease to `current_distinct_kinds - 1`.
                if (distinct_after_removal == current_distinct_kinds) {
                    partner = s;
                    // We found the partner. Leave it removed from the device.
                    break; 
                } else {
                    // s is not the partner. Put it back into the device to restore state for the next check.
                    query(s);
                }
            }

            // We have found the pair (i, partner).
            answer(i, partner);
            pairs_found++;
            paired[i] = true;
            paired[partner] = true;

            // Update the state for the next iteration.
            // The device currently contains (active_slices \ {partner}) U {i}.
            
            // We need to remove i from the device.
            query(i);
            
            // The device now contains (active_slices \ {partner}), which is our new active set.
            // Update the active_slices vector by removing the partner.
            active_slices.erase(std::remove(active_slices.begin(), active_slices.end(), partner), active_slices.end());

            // The number of distinct kinds decreases by one.
            current_distinct_kinds--;
        }

        if (pairs_found == n) {
            break;
        }
    }

    return 0;
}