#include <iostream>
#include <vector>
#include <string>
#include <functional>

using namespace std;

int n;
vector<vector<int>> grid;

int ask(int r1, int c1, int r2, int c2) {
    cout << "? " << r1 << " " << c1 << " " << r2 << " " << c2 << endl;
    int response;
    cin >> response;
    if (response == -1) exit(0);
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

    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            if (grid[i][j] != -1) continue;

            if ((i + j) % 2 == 0) { // White cell
                if (i > 2) {
                    grid[i][j] = grid[i - 2][j] ^ (1 - ask(i - 2, j, i, j));
                } else if (j > 2) {
                    grid[i][j] = grid[i][j - 2] ^ (1 - ask(i, j - 2, i, j));
                } else { // Must be (2,2)
                    grid[2][2] = grid[1][1] ^ (1 - ask(1, 1, 2, 2));
                }
            }
        }
    }

    vector<vector<int>> grid0 = grid;
    vector<vector<int>> grid1 = grid;

    grid0[1][2] = 0;
    grid1[1][2] = 1;

    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            if ((i + j) % 2 == 0) continue;
            if (grid0[i][j] != -1) continue;

            if (i > 2) {
                int res = ask(i - 2, j, i, j);
                grid0[i][j] = grid0[i - 2][j] ^ (1 - res);
                grid1[i][j] = grid1[i - 2][j] ^ (1 - res);
            } else if (j > 2) {
                int res = ask(i, j - 2, i, j);
                grid0[i][j] = grid0[i][j - 2] ^ (1 - res);
                grid1[i][j] = grid1[i][j - 2] ^ (1 - res);
            } else if (i > 1 && j > 1) { // for (2,1)
                int res = ask(i - 1, j - 1, i, j);
                grid0[i][j] = grid0[i - 1][j - 1] ^ (1-res);
                grid1[i][j] = grid1[i - 1][j - 1] ^ (1-res);
            }
        }
    }

    bool res0, res1;
    
    // Check with query ? 1 2 3 1 (invalid)
    // Check with query ? 1 2 2 3
    bool p1_0 = (grid0[1][2] == grid0[2][3]);
    bool p2_0 = (grid0[1][2] == grid0[2][3]);
    res0 = p1_0 || p2_0;

    bool p1_1 = (grid1[1][2] == grid1[2][3]);
    bool p2_1 = (grid1[1][2] == grid1[2][3]);
    res1 = p1_1 || p2_1;

    if (res0 != res1) {
        int final_res = ask(1, 2, 2, 3);
        grid = (final_res == res0) ? grid0 : grid1;
    } else {
        bool p1_0 = (grid0[1][1] == grid0[2][3] && grid0[1][2] == grid0[1][3]);
        bool p2_0 = (grid0[1][1] == grid0[2][3] && grid0[1][2] == grid0[2][2]);
        bool p3_0 = (grid0[1][1] == grid0[2][3] && grid0[2][1] == grid0[2][2]);
        res0 = p1_0 || p2_0 || p3_0;
        
        bool p1_1 = (grid1[1][1] == grid1[2][3] && grid1[1][2] == grid1[1][3]);
        bool p2_1 = (grid1[1][1] == grid1[2][3] && grid1[1][2] == grid1[2][2]);
        bool p3_1 = (grid1[1][1] == grid1[2][3] && grid1[2][1] == grid1[2][2]);
        res1 = p1_1 || p2_1 || p3_1;

        int final_res = ask(1, 1, 2, 3);
        grid = (final_res == res0) ? grid0 : grid1;
    }

    answer();

    return 0;
}