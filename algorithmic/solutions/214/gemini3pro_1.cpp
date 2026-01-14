#include <iostream>
#include <vector>
#include <algorithm>

using namespace std;

// Structure to store operations
struct Op {
    int l, r;
};

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    vector<int> a(n + 1);
    for (int i = 1; i <= n; ++i) {
        cin >> a[i];
    }

    // We choose x = 3.
    // This allows us to reverse segments of length 3+1=4 and 3-1=2.
    // Length 4 effectively moves an element by 3 positions.
    // Length 2 effectively moves an element by 1 position (swap adjacent).
    // This combination is sufficient to sort any permutation.
    // It fits within the 200n limit for partial scoring, typically achieving around n^2/6 operations.
    // This strategy is robust and avoids boundary issues associated with larger x.

    int x = 3;
    vector<Op> ops;
    
    // Reserve memory to avoid reallocations, though not strictly necessary given limits
    ops.reserve(200000);

    // Helper lambda to record and perform reversal
    auto do_reverse = [&](int l, int r) {
        ops.push_back({l, r});
        reverse(a.begin() + l, a.begin() + r + 1);
    };

    // Greedy strategy: place elements 1, 2, ..., n in order.
    for (int i = 1; i <= n; ++i) {
        // Find current position of value i
        // Since 1 to i-1 are already in place, search from i
        int pos = -1;
        for (int j = i; j <= n; ++j) {
            if (a[j] == i) {
                pos = j;
                break;
            }
        }

        // Move a[pos] to position i
        while (pos > i) {
            int dist = pos - i;
            if (dist >= 3) {
                // If distance is large enough, use the larger jump (length 4 reversal)
                // This reverses [pos-3, pos], moving the element at pos to pos-3.
                do_reverse(pos - 3, pos);
                pos -= 3;
            } else {
                // If distance is small (1 or 2), use the smaller step (length 2 reversal)
                // This reverses [pos-1, pos], moving the element at pos to pos-1.
                // Note: length 2 is just a swap of adjacent elements.
                do_reverse(pos - 1, pos);
                pos -= 1;
            }
        }
    }

    // Output results
    cout << x << "\n";
    cout << ops.size() << "\n";
    for (const auto& op : ops) {
        cout << op.l << " " << op.r << "\n";
    }

    return 0;
}