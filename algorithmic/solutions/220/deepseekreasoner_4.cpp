#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    // cards[i] holds the cards of player i (0-indexed), values are 0-indexed (1..n -> 0..n-1)
    vector<vector<int>> cards(n);
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            int x;
            cin >> x;
            --x; // convert to 0-indexed
            cards[i].push_back(x);
        }
    }

    auto is_solid = [&]() {
        for (int i = 0; i < n; ++i) {
            for (int v : cards[i]) {
                if (v != i) return false;
            }
        }
        return true;
    };

    vector<vector<int>> operations;
    int max_ops = n * n - n;
    while (!is_solid() && (int)operations.size() < max_ops) {
        vector<int> pass(n, -1);
        vector<int> remove_idx(n, -1);

        // choose which card each player will pass
        for (int p = 0; p < n; ++p) {
            int best_d = -1, best_val = -1, best_pos = -1;
            for (int i = 0; i < (int)cards[p].size(); ++i) {
                int val = cards[p][i];
                int d = (val - p + n) % n; // distance to target, 0 means already at target
                if (d > best_d) {
                    best_d = d;
                    best_val = val;
                    best_pos = i;
                }
            }
            if (best_d == -1) { // all cards are already the player's own number
                best_val = p;
                best_pos = 0;
            }
            pass[p] = best_val;
            remove_idx[p] = best_pos;
        }

        // remove chosen cards
        for (int p = 0; p < n; ++p) {
            int idx = remove_idx[p];
            cards[p].erase(cards[p].begin() + idx);
        }
        // add passed cards to the right neighbours
        for (int p = 0; p < n; ++p) {
            int q = (p + 1) % n;
            cards[q].push_back(pass[p]);
        }

        // convert to 1-indexed for output
        vector<int> op(n);
        for (int p = 0; p < n; ++p) {
            op[p] = pass[p] + 1;
        }
        operations.push_back(op);
    }

    // output
    cout << operations.size() << "\n";
    for (auto &op : operations) {
        for (int i = 0; i < n; ++i) {
            if (i) cout << " ";
            cout << op[i];
        }
        cout << "\n";
    }

    return 0;
}