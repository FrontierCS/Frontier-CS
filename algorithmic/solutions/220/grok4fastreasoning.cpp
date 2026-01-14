#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<vector<int>> hand(n + 1);
    for (int i = 1; i <= n; i++) {
        for (int j = 0; j < n; j++) {
            int c;
            cin >> c;
            hand[i].push_back(c);
        }
    }
    vector<vector<int>> operations;
    while (true) {
        bool all_solid = true;
        for (int i = 1; i <= n; i++) {
            bool solid = true;
            for (int c : hand[i]) {
                if (c != i) {
                    solid = false;
                    break;
                }
            }
            if (!solid) all_solid = false;
        }
        if (all_solid) break;
        vector<int> pass(n + 1);
        vector<int> indices(n + 1, -1);
        for (int i = 1; i <= n; i++) {
            for (int j = 0; j < (int)hand[i].size(); j++) {
                if (hand[i][j] != i) {
                    pass[i] = hand[i][j];
                    indices[i] = j;
                    break;
                }
            }
            if (indices[i] == -1) {
                pass[i] = hand[i][0];
                indices[i] = 0;
            }
        }
        vector<int> op_line;
        for (int i = 1; i <= n; i++) {
            op_line.push_back(pass[i]);
        }
        operations.push_back(op_line);
        for (int i = 1; i <= n; i++) {
            hand[i].erase(hand[i].begin() + indices[i]);
        }
        for (int i = 1; i <= n; i++) {
            int nextp = (i == n ? 1 : i + 1);
            hand[nextp].push_back(pass[i]);
        }
    }
    cout << operations.size() << endl;
    for (auto& op : operations) {
        for (int j = 0; j < n; j++) {
            cout << op[j];
            if (j < n - 1) cout << " ";
            else cout << endl;
        }
    }
    return 0;
}