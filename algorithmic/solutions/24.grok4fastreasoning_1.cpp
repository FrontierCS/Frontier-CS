#include <bits/stdc++.h>
using namespace std;

bool find_path(int pos, int curr_changes, int last_color, int prev_end, const vector<vector<int>>& c, vector<int>& perm, vector<char>& used, int n) {
    if (pos == n + 1) {
        int cn = c[perm[n]][perm[1]];
        int delta = (cn != last_color ? 1 : 0);
        return curr_changes + delta <= 1;
    }
    for (int j = 1; j <= n; ++j) {
        if (used[j]) continue;
        int new_c = c[prev_end][j];
        int delta = 0;
        if (pos > 2 && new_c != last_color) delta = 1;
        int new_changes = curr_changes + delta;
        if (new_changes > 1) continue;
        perm[pos] = j;
        used[j] = 1;
        if (find_path(pos + 1, new_changes, new_c, j, c, perm, used, n)) return true;
        used[j] = 0;
    }
    return false;
}

int main() {
    int n;
    while (cin >> n) {
        vector<vector<int>> c(n + 1, vector<int>(n + 1, 0));
        for (int i = 1; i <= n; ++i) {
            for (int j = 1; j <= n; ++j) {
                cin >> c[i][j];
            }
        }
        vector<int> perm(n + 1);
        vector<char> used(n + 1, 0);
        bool possible = false;
        int start_p1 = -1;
        for (int p1 = 1; p1 <= n && !possible; ++p1) {
            perm[1] = p1;
            fill(used.begin(), used.end(), 0);
            used[p1] = 1;
            if (find_path(2, 0, 0, p1, c, perm, used, n)) {
                possible = true;
                start_p1 = p1;
            }
        }
        if (possible) {
            for (int i = 1; i <= n; ++i) {
                if (i > 1) cout << " ";
                cout << perm[i];
            }
            cout << endl;
        } else {
            cout << -1 << endl;
        }
    }
    return 0;
}