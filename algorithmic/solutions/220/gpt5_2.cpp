#include <bits/stdc++.h>
using namespace std;

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int n;
    if (!(cin >> n)) return 0;
    vector<vector<int>> cnt(n, vector<int>(n, 0));
    vector<set<int>> wrong(n);
    long long W = 0; // total number of wrong cards
    for (int i = 0; i < n; ++i) {
        for (int k = 0; k < n; ++k) {
            int x; cin >> x; --x;
            cnt[i][x]++;
        }
    }
    // Initialize wrong sets and W
    for (int i = 0; i < n; ++i) {
        for (int l = 0; l < n; ++l) {
            if (l != i && cnt[i][l] > 0) {
                wrong[i].insert(l);
                W += cnt[i][l];
            }
        }
    }
    vector<vector<int>> ans;
    if (W == 0) {
        cout << 0 << "\n";
        return 0;
    }
    int maxOps = n * (n - 1);
    ans.reserve(maxOps);
    for (int step = 0; step < maxOps; ++step) {
        vector<int> moveLabel(n, -1);
        // Decide moves
        for (int j = 0; j < n; ++j) {
            int dest = (j + 1) % n;
            // Prefer to pass a card that becomes correct at dest if possible
            if (cnt[j][dest] > 0) {
                moveLabel[j] = dest;
            } else if (!wrong[j].empty()) {
                // Pass any wrong card
                moveLabel[j] = *wrong[j].begin();
            } else {
                // All cards are correct at j, pass own label
                moveLabel[j] = j;
            }
        }
        // Record for output (convert to 1-based)
        vector<int> out(n);
        for (int j = 0; j < n; ++j) out[j] = moveLabel[j] + 1;
        ans.push_back(out);

        // Update W based on moves (simultaneous)
        for (int j = 0; j < n; ++j) {
            int l = moveLabel[j];
            int dest = (j + 1) % n;
            if (l == j) W += 1;
            else if (l == dest) W -= 1;
        }

        // Apply decrements
        for (int j = 0; j < n; ++j) {
            int l = moveLabel[j];
            cnt[j][l]--;
            if (l != j && cnt[j][l] == 0) {
                wrong[j].erase(l);
            }
        }
        // Apply increments
        for (int j = 0; j < n; ++j) {
            int l = moveLabel[j];
            int dest = (j + 1) % n;
            int prev = cnt[dest][l];
            cnt[dest][l]++;
            if (l != dest && prev == 0) {
                wrong[dest].insert(l);
            }
        }

        if (W == 0) break;
    }

    // Output
    cout << (int)ans.size() << "\n";
    for (auto &row : ans) {
        for (int j = 0; j < n; ++j) {
            if (j) cout << ' ';
            cout << row[j];
        }
        cout << "\n";
    }
    return 0;
}