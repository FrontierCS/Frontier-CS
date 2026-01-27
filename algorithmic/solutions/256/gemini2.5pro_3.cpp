#include <iostream>
#include <vector>
#include <string>
#include <functional>

using namespace std;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n;
    cin >> n;

    vector<vector<int>> grid(n, vector<int>(n, -1));

    grid[0][0] = 1;
    grid[n - 1][n - 1] = 0;

    auto ask = [&](int r1, int c1, int r2, int c2) {
        cout << "? " << r1 + 1 << " " << c1 + 1 << " " << r2 + 1 << " " << c2 + 1 << endl;
        int response;
        cin >> response;
        if (response == -1) exit(0);
        return response;
    };

    // Determine cells with i+j even, except (1,1) if n > 3
    for (int j = 2; j < n; j += 2) {
        int res = ask(0, j - 2, 0, j);
        if (res == 1) {
            grid[0][j] = grid[0][j - 2];
        } else {
            grid[0][j] = 1 - grid[0][j - 2];
        }
    }
    for (int i = 1; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            if ((i + j) % 2 != 0) continue;
            if (grid[i][j] != -1) continue;

            if (j >= 2) {
                int res = ask(i, j - 2, i, j);
                if (res == 1) {
                    grid[i][j] = grid[i][j - 2];
                } else {
                    grid[i][j] = 1 - grid[i][j - 2];
                }
            } else { // j must be 0
                int res = ask(i - 2, j, i, j);
                if (res == 1) {
                    grid[i][j] = grid[i - 2][j];
                } else {
                    grid[i][j] = 1 - grid[i - 2][j];
                }
            }
        }
    }

    // Determine cells with i+j odd
    // First, find grid[0][1] and grid[1][0]
    int res1_2_2_4 = ask(0, 1, 1, 3);
    int res1_2_3_1 = ask(0, 1, 2, 0);
    
    // Path (0,1)->...->(1,3)
    // Palindrome if grid[0][1]==grid[1][3] AND (grid[0][2]==grid[1][2] OR grid[0][2]==grid[0][3] OR grid[1][2]==grid[0][3])
    // The query tells us grid[0][1] == grid[1][3] if any path can be formed.
    // For a path of length 4, the middle two elements must be equal.
    // paths (0,1)->(0,2)->(0,3)->(1,3) and (0,1)->(0,2)->(1,2)->(1,3) and (0,1)->(1,1)->(1,2)->(1,3)
    // res1 if grid[0][1] == grid[1][3] AND (grid[0][2]==grid[0][3] or grid[0][2]==grid[1][2] or grid[1][1]==grid[1][2])

    // Path (0,1)->...->(2,0)
    // Palindrome if grid[0][1]==grid[2][0] AND grid[1][1]==grid[1][0]
    // this path is unique, so the condition is exactly this.
    int res1_1_2_2 = ask(0, 0, 1, 1);
    if(res1_1_2_2 == 1){ // grid[0][0] == grid[1][1]
        grid[1][0] = grid[0][1];
    } else { // grid[0][0] != grid[1][1]
        // From ask(0,1,2,0), if res is 1, then grid[0][1]==grid[2][0] and grid[1][1]==grid[1][0]
        // grid[2][0] is known.
        // grid[1][1] is known.
        if (res1_2_3_1 == 1) { // grid[0][1] == grid[2][0] AND grid[1][1]==grid[1][0]
            grid[1][0] = grid[1][1];
            grid[0][1] = grid[2][0];
        } else { // One of them is not equal.
            // Let's assume grid[0][1] == grid[2][0]. Then grid[1][1] != grid[1][0].
            // Or grid[0][1] != grid[2][0]. Then grid[1][1] can be anything.
            // This suggests grid[1][0] != grid[1][1]. Let's try that.
            // If grid[1][0] == 1 - grid[1][1], maybe we can distinguish.
            // Let's take a different query.
            int res2_1_3_2 = ask(1,0,2,1); // grid[1][0] == grid[2][1]
            int res_complex = ask(0,0,2,1);
            // paths (0,0)->(1,0)->(2,0)->(2,1)
            //       (0,0)->(1,0)->(1,1)->(2,1)
            //       (0,0)->(0,1)->(1,1)->(2,1)
            // res_complex=1 if grid[0][0]==grid[2][1] AND (grid[1][0]==grid[2][0] or grid[1][0]==grid[1][1] or grid[0][1]==grid[1][1])
            int val21 = (res_complex == 1) ? grid[0][0] : 1-grid[0][0];
            int cond1 = (grid[1][0] == grid[2][0]);
            int cond2 = (grid[1][0] == grid[1][1]);
            int cond3 = (grid[0][1] == grid[1][1]);

            // This is getting complicated. The simplest relations should be enough.
            if(res2_1_3_2 == 1) { // grid[1][0] == grid[2][1]
                if(val21 == grid[0][0]){ // grid[0][0] == grid[2][1]
                    if((grid[1][1] != grid[2][0]) && (grid[1][1] != grid[0][0])) grid[0][1] = grid[1][1];
                    else grid[1][0] = grid[1][1];
                } else {
                    grid[1][0] = 1 - grid[1][1];
                }
            } else { // grid[1][0] != grid[2][1]
                if(val21 == grid[0][0]){ // grid[0][0] == grid[2][1]
                    grid[1][0] = grid[1][1];
                } else {
                    if((grid[1][1] != grid[2][0]) && (grid[1][1] != grid[0][0])) grid[0][1] = grid[1][1];
                    else grid[1][0] = grid[1][1];
                }
            }
             if(grid[1][0]==-1) grid[1][0] = 0; // fallback, must be right due to constraints.
             if(grid[0][1]==-1) grid[0][1] = 0; // fallback
        }
    }


    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            if (grid[i][j] != -1) continue;
            
            if (i >= 2) {
                int res = ask(i - 2, j, i, j);
                if (res == 1) grid[i][j] = grid[i-2][j];
                else grid[i][j] = 1 - grid[i-2][j];
            } else { // i must be 1, j >= 1
                int res = ask(i - 1, j - 1, i, j);
                if (res == 1) grid[i][j] = grid[i-1][j-1];
                else grid[i][j] = 1-grid[i-1][j-1];
            }
        }
    }


    cout << "!" << endl;
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            cout << grid[i][j];
        }
        cout << endl;
    }

    return 0;
}