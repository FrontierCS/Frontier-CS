#include <iostream>
#include <vector>
#include <numeric>
#include <random>
#include <algorithm>

// Function to perform a query
int ask(int x) {
    std::cout << "? " << x << std::endl;
    int r;
    std::cin >> r;
    if (r == -1) exit(0); // Judge may terminate on error
    return r;
}

// Function to report a pair
void answer(int a, int b) {
    std::cout << "! " << a << " " << b << std::endl;
}

void solve(std::vector<int>& slices) {
    if (slices.empty()) {
        return;
    }
    if (slices.size() == 2) {
        answer(slices[0], slices[1]);
        return;
    }

    // Pick a pivot element. Slices are pre-shuffled, so this is a random pivot.
    int pivot = slices.back();
    slices.pop_back();

    // Put pivot in the device.
    ask(pivot);

    std::vector<int> group_with_pivot;
    group_with_pivot.push_back(pivot);
    std::vector<int> other_group;

    // The number of distinct kinds in the device.
    // Initially, only the pivot is in, so there's 1 kind.
    int kinds_in_device = 1;

    // Partition the remaining slices based on the pivot.
    for (int slice : slices) {
        int kinds_after_toggle = ask(slice);
        // If the number of kinds does not increase, the new slice's mate is
        // already in the device. The device currently contains group_with_pivot.
        if (kinds_after_toggle == kinds_in_device) {
            group_with_pivot.push_back(slice);
        } else {
            // Number of kinds increased, so slice's mate is not in group_with_pivot.
            // This slice belongs to a different self-contained group.
            other_group.push_back(slice);
            // The slice was added and increased kinds, so we update the count for the
            // growing set in the device.
            kinds_in_device = kinds_after_toggle;
        }
    }

    // At this point, group_with_pivot is in the device.
    // Its elements form a self-contained set.
    // The elements of other_group are not in the device and also form a self-contained set.

    // Clear the device by removing all elements of group_with_pivot.
    for (int slice : group_with_pivot) {
        ask(slice);
    }
    
    // Recurse on both groups.
    solve(group_with_pivot);
    solve(other_group);
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    int n;
    std::cin >> n;

    if (n == 0) {
        return 0;
    }

    std::vector<int> all_slices(2 * n);
    std::iota(all_slices.begin(), all_slices.end(), 1);

    // Randomize to make worst-case pivot selection highly unlikely.
    std::random_device rd;
    std::mt19937 g(rd());
    std::shuffle(all_slices.begin(), all_slices.end(), g);

    solve(all_slices);

    return 0;
}