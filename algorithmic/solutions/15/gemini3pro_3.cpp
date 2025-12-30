#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

// Function to apply operation on vector p
void apply_op(vector<int>& p, int x, int y) {
    int n = p.size();
    // A is prefix of length x
    // B is middle
    // C is suffix of length y
    vector<int> A(p.begin(), p.begin() + x);
    vector<int> B(p.begin() + x, p.end() - y);
    vector<int> C(p.end() - y, p.end());
    
    // Result C B A
    vector<int> res;
    res.reserve(n);
    res.insert(res.end(), C.begin(), C.end());
    res.insert(res.end(), B.begin(), B.end());
    res.insert(res.end(), A.begin(), A.end());
    p = res;
}

// Function to count inversions to determine parity
int count_inversions(const vector<int>& p) {
    int inv = 0;
    int n = p.size();
    for (int i = 0; i < n; ++i) {
        for (int j = i + 1; j < n; ++j) {
            if (p[i] > p[j]) inv++;
        }
    }
    return inv;
}

struct Move {
    int x, y;
};

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    int n;
    if (!(cin >> n)) return 0;
    vector<int> p(n);
    for (int i = 0; i < n; ++i) cin >> p[i];

    // Handle small N=3 separately as the strategy differs due to small size
    if (n == 3) {
        // Only one possible non-identity operation: x=1, y=1
        // Applying it twice creates a cycle of period 2 or identity.
        // We just check if applying one op improves the lexicographical order.
        vector<int> p0 = p;
        vector<int> p1 = p;
        apply_op(p1, 1, 1);
        
        if (p1 < p0) {
            cout << 1 << "\n";
            cout << "1 1" << "\n";
        } else {
            cout << 0 << "\n";
        }
        return 0;
    }

    // For N >= 4, we use a constructive algorithm
    vector<Move> ops;
    
    // Check parity. The standard operations in the greedy phase preserve parity.
    // If current parity is Odd (inv is Odd), we must flip it to Even (target 1,2,...n is Even).
    // Op(1, 1) always toggles parity for N >= 3 (change is 2n-3 which is Odd).
    int inv = count_inversions(p);
    if (inv % 2 != 0) {
        apply_op(p, 1, 1);
        ops.push_back({1, 1});
    }

    // Greedy phase: Place i at position i for i = 1 to n-2
    for (int i = 1; i <= n - 2; ++i) {
        // Find current position of value i
        int k = -1;
        for (int idx = 0; idx < n; ++idx) {
            if (p[idx] == i) {
                k = idx + 1; // 1-based index
                break;
            }
        }
        
        if (k == i) continue; // Already in place

        if (i == 1) {
            // Special handling for placing 1 because there is no sorted prefix L yet
            if (k == n) {
                // If 1 is at the end, swap prefix(1) and suffix(1) -> 1 moves to front
                apply_op(p, 1, 1);
                ops.push_back({1, 1});
            } else if (k == 2) {
                // If 1 is at pos 2, move it to end first, then apply k=n logic logic or specialized
                // Op(1, n-2) moves 1 from pos 2 to pos n-1
                apply_op(p, 1, n - 2);
                ops.push_back({1, n - 2});
                // Now 1 is at n-1. Apply logic for k > 2 (specifically k=n-1)
                // New k is n-1. Op(1, n-(n-1)+1) = Op(1, 2)
                apply_op(p, 1, 2);
                ops.push_back({1, 2});
            } else {
                // 2 < k < n
                // Op(1, n - k + 1) brings element at k to front
                apply_op(p, 1, n - k + 1);
                ops.push_back({1, n - k + 1});
            }
        } else {
            // i > 1, so L = i-1 >= 1. Sorted prefix exists.
            int L = i - 1;
            if (k < n) {
                // Standard 2-op move for k < n
                // 1. Move S to end, bring target to roughly front
                apply_op(p, L, 1);
                ops.push_back({L, 1});
                
                // 2. Restore S to front, placing target immediately after S
                apply_op(p, k - i + 1, L);
                ops.push_back({k - i + 1, L});
            } else {
                // k = n. Target is at the very end.
                // 1. Move S to end, bring last 2 elements to front
                apply_op(p, L, 2);
                ops.push_back({L, 2});
                
                // 2. Restore S, placing target (which was at n, now at 2) to correct spot
                apply_op(p, 1, L);
                ops.push_back({1, L});
            }
        }
    }

    cout << ops.size() << "\n";
    for (auto m : ops) {
        cout << m.x << " " << m.y << "\n";
    }

    return 0;
}