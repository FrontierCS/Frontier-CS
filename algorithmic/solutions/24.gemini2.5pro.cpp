#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>

using namespace std;

int n;
vector<vector<int>> C;
vector<int> p;
vector<bool> used;
bool solution_found;

void solve_recursive(int k, int changes_in_prefix) {
    if (solution_found) {
        return;
    }

    if (changes_in_prefix > 1) {
        return;
    }

    if (k > n) {
        vector<int> c(n + 1);
        for (int i = 1; i < n; ++i) {
            c[i] = C[p[i]][p[i + 1]];
        }
        c[n] = C[p[n]][p[1]];

        int total_changes = 0;
        for (int i = 1; i < n; ++i) {
            if (c[i] != c[i + 1]) {
                total_changes++;
            }
        }

        if (total_changes <= 1) {
            solution_found = true;
            for (int i = 1; i <= n; ++i) {
                cout << p[i] << (i == n ? "" : " ");
            }
            cout << endl;
        }
        return;
    }

    for (int i = 1; i <= n; ++i) {
        if (!used[i]) {
            p[k] = i;
            used[i] = true;
            
            int new_changes = changes_in_prefix;
            if (k >= 3) {
                if (C[p[k - 2]][p[k - 1]] != C[p[k - 1]][p[k]]) {
                    new_changes++;
                }
            }
            
            solve_recursive(k + 1, new_changes);
            
            if (solution_found) {
                return;
            }
            
            used[i] = false;
        }
    }
}

void run_test_case() {
    p.assign(n + 1, 0);
    used.assign(n + 1, false);
    solution_found = false;

    solve_recursive(1, 0);

    if (!solution_found) {
        cout << -1 << endl;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    while (cin >> n) {
        C.assign(n + 1, vector<int>(n + 1));
        string row_str;
        for (int i = 1; i <= n; ++i) {
            cin >> row_str;
            for (int j = 1; j <= n; ++j) {
                C[i][j] = row_str[j - 1] - '0';
            }
        }
        run_test_case();
    }

    return 0;
}