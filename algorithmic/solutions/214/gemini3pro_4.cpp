#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Global variables to store the sequence and operations
int n;
vector<int> a;
struct Op {
    int l, r;
};
vector<Op> ops;

// Function to apply reversal and record it
void apply_op(int l, int r) {
    ops.push_back({l, r});
    reverse(a.begin() + l, a.begin() + r + 1);
}

// Move element at index `curr` to `target` (where curr > target)
// We use x=3, so allowed lengths are 2 and 4.
// Length 4 reversal [i, i+3] moves a[i+3] to a[i] (Jump 3 steps left, scrambling intermediate)
// Length 2 reversal [i, i+1] moves a[i+1] to a[i] (Jump 1 step left, swapping adjacent)
void move_left(int curr, int target) {
    while (curr > target) {
        // Prefer jump 3 (length 4) for efficiency
        if (curr - target >= 3) {
            apply_op(curr - 3, curr);
            curr -= 3;
        } else {
            // Fallback to jump 1 (length 2)
            apply_op(curr - 1, curr);
            curr -= 1;
        }
    }
}

// Recursive Quicksort-like function
// L, R: current index range in array a
// v_min, v_max: the range of values expected in a[L...R]
void quicksort(int L, int R, int v_min, int v_max) {
    if (L >= R) return;
    if (v_min == v_max) return;

    // Optimization: Check if current range is already sorted
    bool sorted = true;
    for (int i = L; i <= R; ++i) {
        if (a[i] != v_min + (i - L)) {
            sorted = false;
            break;
        }
    }
    if (sorted) return;

    int pivot = (v_min + v_max) / 2;
    int split = L - 1; // Points to the last element of the "left" partition

    // Partition logic: Stable partition based on value
    // We iterate through the range. If we find an element <= pivot,
    // we move it to the position immediately after 'split'.
    // The elements > pivot are pushed to the right (and possibly scrambled internally).
    for (int i = L; i <= R; ++i) {
        if (a[i] <= pivot) {
            // This element belongs to the left part
            // Target position is split + 1
            if (i > split + 1) {
                move_left(i, split + 1);
            }
            split++;
        }
    }

    // Recurse on sub-ranges
    // Left part: indices [L, split], values [v_min, pivot]
    quicksort(L, split, v_min, pivot);
    // Right part: indices [split+1, R], values [pivot+1, v_max]
    quicksort(split + 1, R, pivot + 1, v_max);
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n)) return 0;

    a.resize(n + 1);
    for (int i = 1; i <= n; ++i) {
        cin >> a[i];
    }

    // We choose x = 3, which allows reversals of length 2 (adjacent swap) and 4 (block move).
    // This enables efficient O(N log N) sorting.
    quicksort(1, n, 1, n);

    // Output results
    cout << 3 << "\n";
    cout << ops.size() << "\n";
    for (const auto& op : ops) {
        cout << op.l << " " << op.r << "\n";
    }

    return 0;
}