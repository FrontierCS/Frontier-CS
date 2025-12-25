#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>

using namespace std;

int n;
vector<int> p;
vector<pair<int, int>> ops;
vector<int> pos;

void apply_op(int x, int y) {
    if (x <= 0 || y <= 0 || x + y >= n) {
        return;
    }
    ops.push_back({x, y});
    
    vector<int> next_p;
    
    // Suffix
    for (int i = n - y; i < n; ++i) next_p.push_back(p[i]);
    // Middle
    for (int i = x; i < n - y; ++i) next_p.push_back(p[i]);
    // Prefix
    for (int i = 0; i < x; ++i) next_p.push_back(p[i]);
    
    p = next_p;

    for (int i = 0; i < n; ++i) {
        pos[p[i]] = i;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n;
    p.resize(n);
    pos.resize(n + 1);
    for (int i = 0; i < n; ++i) {
        cin >> p[i];
        pos[p[i]] = i;
    }

    if (n == 3 && p[1] != 2) {
        // For n=3, the only operation is (1,1), which swaps p[0] and p[2].
        // The middle element p[1] is an invariant.
        // The best we can do is sort p[0] and p[2].
        if (p[0] > p[2]) {
            apply_op(1, 1);
        }
    } else {
        for (int i = 1; i <= n; ++i) {
            int current_pos = pos[i];
            int target_pos = i - 1;

            if (current_pos == target_pos) {
                continue;
            }

            // Phase 1: Move element `i` from `current_pos` to `n-1`.
            if (current_pos != n - 1) {
                if (current_pos == n - 2) {
                    apply_op(n - 2, 1);
                    apply_op(2, 1);
                } else {
                    apply_op(current_pos + 1, 1);
                }
            }
            
            // Now element `i` is at `n-1`.
            current_pos = pos[i]; // This will be n-1
            
            // Phase 2: Move element `i` from `n-1` to `target_pos`.
            if (target_pos != n - 1) {
                // This is a right cyclic shift on p[target_pos..n-1]
                if (target_pos > 0) {
                    apply_op(target_pos, 1);
                }
                
                apply_op(1, n - 1 - target_pos);

                if (target_pos > 0) {
                    apply_op(n - target_pos, target_pos);
                }
            }
        }
    }

    cout << ops.size() << "\n";
    for (const auto& op : ops) {
        cout << op.first << " " << op.second << "\n";
    }

    return 0;
}