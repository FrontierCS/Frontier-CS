#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);

    int n;
    cin >> n;
    vector<int> p(n);
    for (int i = 0; i < n; ++i) {
        cin >> p[i];
    }

    // Groups: 0 -> a (increasing), 1 -> b (decreasing), 2 -> c (increasing), 3 -> d (decreasing)
    vector<vector<int>> groups(4);
    vector<int> last(4);
    last[0] = 0;          // increasing groups start with 0
    last[2] = 0;
    last[1] = n + 1;      // decreasing groups start with n+1
    last[3] = n + 1;

    for (int x : p) {
        int best_idx = -1;
        int best_val = 2 * n + 5; // a large number

        // First, try feasible groups (where monotonicity is preserved)
        for (int idx = 0; idx < 4; ++idx) {
            bool feasible = false;
            if (idx == 0 || idx == 2) { // increasing groups
                feasible = (x > last[idx]);
            } else { // decreasing groups
                feasible = (x < last[idx]);
            }
            if (feasible) {
                int gap = abs(x - last[idx]);
                if (gap < best_val) {
                    best_val = gap;
                    best_idx = idx;
                }
            }
        }

        // If no feasible group, choose the one with minimal violation
        if (best_idx == -1) {
            for (int idx = 0; idx < 4; ++idx) {
                int violation = abs(x - last[idx]);
                if (violation < best_val) {
                    best_val = violation;
                    best_idx = idx;
                }
            }
        }

        // Assign x to the chosen group
        groups[best_idx].push_back(x);
        last[best_idx] = x;
    }

    // Output
    cout << groups[0].size() << " " << groups[1].size() << " "
         << groups[2].size() << " " << groups[3].size() << "\n";

    for (int g = 0; g < 4; ++g) {
        if (!groups[g].empty()) {
            for (size_t i = 0; i < groups[g].size(); ++i) {
                cout << groups[g][i] << (i + 1 == groups[g].size() ? "\n" : " ");
            }
        } else {
            cout << "\n";
        }
    }

    return 0;
}