#include <iostream>
#include <vector>
#include <string>
#include <numeric>

using namespace std;

int n;
vector<vector<int>> grid;

int ask(int r1, int c1, int r2, int c2) {
    cout << "? " << r1 << " " << c1 << " " << r2 << " " << c2 << endl;
    int response;
    cin >> response;
    if (response == -1) {
        exit(0);
    }
    return response;
}

void answer() {
    cout << "!" << endl;
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            cout << grid[i][j];
        }
        cout << endl;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n;
    grid.assign(n + 1, vector<int>(n + 1, -1));

    grid[1][1] = 1;
    grid[n][n] = 0;

    // Fill even parity cells
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            if ((i + j) % 2 != 0) continue;
            if (grid[i][j] != -1) continue;

            if (i > 2) {
                int res = ask(i - 2, j, i, j);
                grid[i][j] = (res == 1) ? grid[i - 2][j] : 1 - grid[i - 2][j];
            } else {
                int res = ask(i, j - 2, i, j);
                grid[i][j] = (res == 1) ? grid[i][j - 2] : 1 - grid[i][j - 2];
            }
        }
    }

    // Tentatively fill odd parity cells, creating two candidate grids
    vector<vector<int>> grid0 = grid;
    grid0[1][2] = 0;
    
    // Fill remaining odd parity cells for grid0
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            if ((i + j) % 2 == 0 || grid0[i][j] != -1) continue;

            if (j > 2) {
                grid0[i][j] = (ask(i, j - 2, i, j) == 1) ? grid0[i][j - 2] : 1 - grid0[i][j - 2];
            } else if (i > 2) {
                grid0[i][j] = (ask(i - 2, j, i, j) == 1) ? grid0[i - 2][j] : 1 - grid0[i - 2][j];
            } else { // i=2, j=1
                int res = ask(i - 1, j, i, j + 1);
                grid0[i][j] = (res == 1) ? grid0[i - 1][j + 1] : 1 - grid0[i - 1][j + 1];
            }
        }
    }

    vector<vector<int>> grid1 = grid0;
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            if ((i + j) % 2 != 0) {
                grid1[i][j] = 1 - grid0[i][j];
            }
        }
    }

    // Find a query to distinguish grid0 and grid1
    int x1 = -1, y1, x2, y2;
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            if ((i + j) % 2 != 0) { // Cell from Set O
                int k = i + 1, l = j + 1;
                if (k <= n && l <= n) { // Partner from Set O
                    if (grid0[i][j] != grid0[k][l]) {
                        x1 = i; y1 = j; x2 = k + 1; y2 = l;
                        if (x2 <= n && y2 <= n && ((x1+y1)%2 != (x2+y2)%2)) {
                            goto found;
                        }
                    }
                }
            }
        }
    }
    
found:
    int r = ask(x1, y1, x2, y2);

    bool p0_exists = false;
    // Check for palindromic paths in grid0
    if (grid0[x1][y1] == grid0[x2][y2]) {
        // Path len 4, check middle part
        // We only need to check one path. This is a simplification but should be sufficient.
        if (grid0[x1 + 1][y1] == grid0[x2 - 1][y2] || grid0[x1][y1 + 1] == grid0[x2][y2 - 1]) {
             p0_exists = true;
        }
    }

    if (r == p0_exists) {
        grid = grid0;
    } else {
        grid = grid1;
    }

    answer();

    return 0;
}