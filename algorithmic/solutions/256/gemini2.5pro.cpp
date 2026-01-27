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
            if (i == 1 && j == 1) continue;
            if ((i + j) % 2 == 0) { // Cells with even coordinate sum
                if (j >= 3) {
                    int res = ask(i, j - 2, i, j);
                    grid[i][j] = (res == 1) ? grid[i][j - 2] : 1 - grid[i][j - 2];
                } else { // j=1 or j=2. Since i+j is even, i and j have same parity.
                         // For j=1, i is odd. For j=2, i is even.
                    if (i >= 3) {
                         int res = ask(i - 2, j, i, j);
                         grid[i][j] = (res == 1) ? grid[i - 2][j] : 1 - grid[i-2][j];
                    } else { // i=2, j=2. Needs (1,1) as predecessor
                         int res = ask(1, 1, 2, 2);
                         grid[2][2] = (res == 1) ? grid[1][1] : 1 - grid[1][1];
                    }
                }
            }
        }
    }

    // After this, all cells (i,j) with i+j even are determined.
    // Now determine cells with i+j odd.
    // These values can be determined if we know one of them, e.g. grid[1][2].
    // Let's determine grid[1][2] and grid[2][1]
    
    // Determine grid[2][1] first
    // Query ? 1 2 3 1 invalid.
    // Query ? 2 1 1 3 invalid.
    // Let's use a query that relates a black cell with two white cells.
    // ? 1,2 -> 3,2. Path length 3. ans=1 => grid[1][2]==grid[3][2]
    // grid[3][2] is black, unknown.
    // Let's use a query with a known endpoint.
    // ? 1,2 -> 3,3. Path len 4. grid[3][3] is white, known since 3+3 is even.
    int v33 = grid[3][3];
    int res = ask(1, 2, 3, 3);
    int v22 = grid[2][2];
    int v13 = grid[1][3];

    // Response 1 means grid[1][2]==v33 AND exists a palindromic path.
    // Paths from (1,2) to (3,3):
    // ... ->(2,2)->(2,3)->...
    // ... ->(1,3)->(2,3)->...
    // ... ->(2,2)->(3,2)->...
    // Palindrome conditions on inner pairs:
    // grid[2][2]==grid[2][3] OR grid[1][3]==grid[2][3] OR grid[2][2]==grid[3][2]
    
    // We can determine all black cells relative to each other.
    // Let's find grid[1][2] and grid[2][1] first.
    int v12_is_v32 = ask(1,2,3,2);
    int v21_is_v32 = ask(2,1,3,2);
    int v12_is_v21 = (v12_is_v32 == v21_is_v32);
    
    // Let's find grid[1][2]
    // Using ? 1 2 2 3 is not enough. Need a known value.
    // Using ? 2 1 4 1, grid[4][1] is known. relates grid[2][1] to grid[4][1].
    // Path (2,1)->(3,1)->(4,1). Palindrome if grid[2][1]==grid[4][1]
    grid[2][1] = (ask(2,1,4,1) == 1) ? grid[4][1] : 1 - grid[4][1];
    if (v12_is_v21) {
        grid[1][2] = grid[2][1];
    } else {
        grid[1][2] = 1 - grid[2][1];
    }

    // Now fill the rest of the black cells
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            if (grid[i][j] != -1) continue;
            if (j >= 3) {
                grid[i][j] = (ask(i, j - 2, i, j) == 1) ? grid[i][j - 2] : 1 - grid[i][j - 2];
            } else { // j=1 or j=2
                 if (i >= 3) {
                    grid[i][j] = (ask(i-2, j, i, j) == 1) ? grid[i-2][j] : 1 - grid[i-2][j];
                 }
            }
        }
    }

    answer();

    return 0;
}