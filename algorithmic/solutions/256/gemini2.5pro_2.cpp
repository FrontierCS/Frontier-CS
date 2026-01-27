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
    if (response == -1) {
        exit(0);
    }
    return response;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> n;
    grid.assign(n + 1, vector<int>(n + 1, -1));

    grid[1][1] = 1;
    grid[n][n] = 0;

    // Determine cells with even i+j
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            if ((i + j) % 2 != 0 || grid[i][j] != -1) {
                continue;
            }
            if (i > 2) {
                int res = ask(i - 2, j, i, j);
                grid[i][j] = (res == 1) ? grid[i - 2][j] : (1 - grid[i - 2][j]);
            } else if (j > 2) {
                int res = ask(i, j - 2, i, j);
                grid[i][j] = (res == 1) ? grid[i][j - 2] : (1 - grid[i][j - 2]);
            } else if (i > 1 && j > 1) { // (2,2)
                int res = ask(i-1, j-1, i, j);
                grid[i][j] = (res == 1) ? grid[i - 1][j - 1] : (1 - grid[i - 1][j - 1]);
            }
        }
    }

    // Determine cells with odd i+j
    // First, determine (1,2)
    int res = ask(1, 1, 1, 3);
    grid[1][3] = (res == 1) ? grid[1][1] : (1-grid[1][1]);
    
    res = ask(1, 2, 3, 2);
    int res2 = ask(1,2,2,3);
    if(res == 1) { // grid[1][2] == grid[3][2]
      if(res2 == 1) { // grid[1][2] == grid[2][3]
        int res3 = ask(2,3,3,2);
        if(res3==1) { // grid[2][3]==grid[3][2]
          // all three are equal, can't decide
        } else { // grid[2][3] != grid[3][2]
          // this is a contradiction, this case won't happen
        }
      } else { // grid[1][2] != grid[2][3]
        int res3 = ask(2,2,3,3); // grid[2][2] is known from (1,1)
        grid[3][3] = (res3 == 1) ? grid[2][2] : (1-grid[2][2]);
        int res4 = ask(1,2,3,3);
        grid[1][2] = (res4 == 1) ? grid[3][3] : (1 - grid[3][3]);
      }
    } else { // grid[1][2] != grid[3][2]
      res = ask(2,1,3,2);
      if(res == 1) { // grid[2][1] == grid[3][2]
        grid[1][2] = 1 - grid[2][1]; // need grid[2][1]
      } else { // grid[2][1] != grid[3][2]
        // grid[1][2] and grid[2][1] could be anything wrt grid[3][2]
      }
    }
    
    // The logic above is complex. A simpler approach might be needed.
    // Let's brute force the two key unknown cells.
    int b12_cand = -1, b21_cand = -1;

    for (int b12 = 0; b12 <= 1; ++b12) {
        for (int b21 = 0; b21 <= 1; ++b21) {
            grid[1][2] = b12;
            grid[2][1] = b21;
            
            auto get_val = [&](int r, int c) {
                if(grid[r][c] != -1) return grid[r][c];
                if ((r+c)%2 != 0) { // odd i+j depends on (1,2) or (2,1)
                    if((r%2) != (c%2)) { // diff parity
                        if (r % 2 != 1 || c % 2 != 0) { // not (odd, even) like (1,2)
                            return grid[2][1] ^ ((r-2+c-1)/2 % 2);
                        } else {
                            return grid[1][2] ^ ((r-1+c-2)/2 % 2);
                        }
                    }
                }
                return -1; // Should not happen
            };

            // check with a known constraint
            int res1123 = ask(1,1,2,3);
            int v23 = (ask(1,2,2,3) == 1) ? get_val(1,2) : (1-get_val(1,2));
            bool possible = false;
            if(grid[1][1] == v23) {
                if(get_val(1,2) == grid[1][3] || get_val(1,2) == grid[2][2] || get_val(2,1) == grid[2][2]) {
                    possible = true;
                }
            }
            if(possible == (res1123 == 1)) {
                b12_cand = b12;
                b21_cand = b21;
            }
        }
    }
    
    grid[1][2] = b12_cand;
    grid[2][1] = b21_cand;

    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            if (grid[i][j] != -1) continue;
            // All even i+j are filled. Only odd i+j remain.
            if (j > 2) {
                int res = ask(i, j - 2, i, j);
                grid[i][j] = (res == 1) ? grid[i][j-2] : (1 - grid[i][j-2]);
            } else { // j=1 or j=2
                int res = ask(i-2, j, i, j);
                grid[i][j] = (res == 1) ? grid[i-2][j] : (1 - grid[i-2][j]);
            }
        }
    }


    cout << "!" << endl;
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            cout << grid[i][j];
        }
        cout << endl;
    }

    return 0;
}