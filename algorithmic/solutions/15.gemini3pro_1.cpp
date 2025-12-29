#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

// Function to simulate the operation
// x: length of prefix, y: length of suffix
// Returns the new permutation
vector<int> operate(const vector<int>& p, int x, int y) {
    int n = p.size();
    vector<int> res;
    res.reserve(n);
    // Suffix
    for (int i = n - y; i < n; ++i) res.push_back(p[i]);
    // Middle
    for (int i = x; i < n - y; ++i) res.push_back(p[i]);
    // Prefix
    for (int i = 0; i < x; ++i) res.push_back(p[i]);
    return res;
}

struct Op {
    int x, y;
};

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    if (!(cin >> n)) return 0;

    vector<int> p(n);
    for (int i = 0; i < n; ++i) {
        cin >> p[i];
    }

    vector<Op> ops;

    // Helper to perform and record op
    auto do_op = [&](int x, int y) {
        ops.push_back({x, y});
        p = operate(p, x, y);
    };

    // Find position of value v
    auto find_pos = [&](int v) {
        for (int i = 0; i < n; ++i) {
            if (p[i] == v) return i;
        }
        return -1;
    };

    // Step 1: Place 1 at index 0
    int pos1 = find_pos(1);
    if (pos1 != 0) {
        if (pos1 == n - 1) {
            // 1 is at end
            do_op(1, 1);
        } else {
            // 1 is in middle
            // A 1 B
            // Move 1 to end first: Pre A+1, Suf B -> B A 1
            int lenA = pos1;
            int lenB = n - 1 - pos1;
            do_op(lenA + 1, lenB);
            // Now 1 is at end, move to front: Pre 1, Suf 1 (dummy) - No
            // Array is B A 1. Use 1 at end logic: Pre 1, Suf 1 -> 1 ... (if n >= 3, which is true)
            // Actually, we can just swap first and last if 1 is at end and we want it at front.
            // B A 1 -> split x=1, y=1 -> 1 A B[shifted] 
            // Wait, B A 1 -> Op(1, 1): 1 A B[first]... 
            // Simply use x=n-1, y=1?
            // B A (len n-1), 1 (len 1).
            // Op(n-1, 1): 1 (mid empty?) No, mid must be > 0.
            // Use Op(1, 1) on B A 1.
            // Pre B[0], Mid ..., Suf 1.
            // -> 1 ... B[0].
            do_op(1, 1);
        }
    }

    // Invariant: p[0...val-2] contains 1...val-1 sorted.
    for (int val = 2; val <= n; ++val) {
        int pos = find_pos(val);
        // Target position is val-1
        if (pos == val - 1) continue;

        // Current state: P (0..val-2), ..., val (at pos), ...
        // P is sorted 1..val-1.
        
        // Check if val is at end
        if (pos == n - 1) {
            // Special handling for the second to last element sorting (val = n-1)
            // P contains 1..n-2. Array is P n n-1.
            if (val == n - 1) {
                 // P' p_last n n-1 -> P' p_last n-1 n
                 // Op 1: Pre P (len n-2), Suf n-1 (1). -> n-1 n P. (Moves P to end)
                 // This doesn't look right.
                 // Correct sequence derived:
                 // Start: P' p_last n n-1
                 // Op 1: Pre P' p_last, Suf n-1. -> n-1 n P' p_last.
                 // Op 2: Pre n-1 n, Suf P'. -> P' p_last n-1 n.
                 do_op(n - 2, 1);
                 do_op(2, n - 3);
                 continue;
            }

            // General case x at end, B non-empty.
            // P B x -> P B_rest x b1
            int lenP = val - 1;
            // int lenB = (n - 1) - lenP; 
            
            do_op(lenP, 1);
            do_op(2, lenP);
            // Update pos: x is now at n-2
            pos = n - 2;
        }

        // Case: x not at end
        // P ... x A
        // We want P x ... A
        int lenP = val - 1;
        int lenA = n - 1 - pos;
        int lenB = pos - lenP;
        
        do_op(lenP, lenA);
        do_op(lenA + lenB, lenP);
    }

    cout << ops.size() << "\n";
    for (const auto& op : ops) {
        cout << op.x << " " << op.y << "\n";
    }

    return 0;
}