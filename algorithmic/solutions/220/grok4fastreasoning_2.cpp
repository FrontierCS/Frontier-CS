#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<vector<int>> count(n + 1, vector<int>(n + 1, 0));
    for (int i = 1; i <= n; i++) {
        for (int j = 0; j < n; j++) {
            int c;
            cin >> c;
            count[i][c]++;
        }
    }
    vector<vector<int>> ops;
    while (true) {
        bool done = true;
        for (int i = 1; i <= n; i++) {
            if (count[i][i] != n) {
                done = false;
                break;
            }
        }
        if (done) break;
        vector<int> pass(n + 1, 0);
        for (int i = 1; i <= n; i++) {
            int max_d = -1;
            int ch = -1;
            for (int j = 1; j <= n; j++) {
                if (count[i][j] > 0) {
                    int d = (j - i + n) % n;
                    if (d > max_d || (d == max_d && j > ch)) {
                        max_d = d;
                        ch = j;
                    }
                }
            }
            pass[i] = ch;
        }
        for (int i = 1; i <= n; i++) {
            count[i][pass[i]]--;
        }
        for (int i = 1; i <= n; i++) {
            int from = (i == 1 ? n : i - 1);
            int rec = pass[from];
            count[i][rec]++;
        }
        vector<int> thisop(n + 1);
        for (int i = 1; i <= n; i++) {
            thisop[i] = pass[i];
        }
        ops.push_back(thisop);
    }
    cout << ops.size() << endl;
    for (auto& op : ops) {
        for (int i = 1; i <= n; i++) {
            cout << op[i];
            if (i < n) cout << " ";
            else cout << "\n";
        }
    }
    return 0;
}