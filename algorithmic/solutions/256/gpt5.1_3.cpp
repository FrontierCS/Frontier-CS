#include <bits/stdc++.h>
using namespace std;

const int MAXN = 50;

int n;

int evenVal[MAXN + 1][MAXN + 1];
bool evenKnown[MAXN + 1][MAXN + 1];

int rel1[MAXN + 1][MAXN + 1];
int rel2[MAXN + 1][MAXN + 1];
int relOdd[MAXN + 1][MAXN + 1];

int gridVal[2][MAXN + 1][MAXN + 1];

static bool F[2][MAXN + 1][MAXN + 1][MAXN + 1][MAXN + 1];

int ask(int x1, int y1, int x2, int y2) {
    cout << "? " << x1 << " " << y1 << " " << x2 << " " << y2 << '\n';
    cout.flush();
    int res;
    if (!(cin >> res)) exit(0);
    if (res == -1) exit(0);
    return res;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    if (!(cin >> n)) return 0;

    // Initialize known even cells
    memset(evenKnown, 0, sizeof(evenKnown));
    evenVal[1][1] = 1;
    evenKnown[1][1] = true;
    evenVal[n][n] = 0;
    evenKnown[n][n] = true;

    // Determine all even-sum cells using distance-2 equality queries
    for (int sum = 3; sum <= 2 * n; ++sum) {
        for (int x = 1; x <= n; ++x) {
            int y = sum - x;
            if (y < 1 || y > n) continue;
            if ((x + y) % 2 != 0) continue;
            if ((x == 1 && y == 1) || (x == n && y == n)) continue;

            int px = -1, py = -1;
            if (x >= 3) {
                px = x - 2;
                py = y;
            } else if (y >= 3) {
                px = x;
                py = y - 2;
            } else {
                px = x - 1;
                py = y - 1;
            }

            if (!evenKnown[px][py]) {
                if (x >= 3 && evenKnown[x - 2][y]) {
                    px = x - 2; py = y;
                } else if (y >= 3 && evenKnown[x][y - 2]) {
                    px = x; py = y - 2;
                } else if (x >= 2 && y >= 2 && evenKnown[x - 1][y - 1]) {
                    px = x - 1; py = y - 1;
                }
            }

            int res = ask(px, py, x, y); // res == 1 iff values equal
            evenVal[x][y] = res ? evenVal[px][py] : (evenVal[px][py] ^ 1);
            evenKnown[x][y] = true;
        }
    }

    // Determine relative values for odd cells using two BFSs
    memset(rel1, -1, sizeof(rel1));
    memset(rel2, -1, sizeof(rel2));

    // BFS1 from (1,2)
    if (n >= 2) {
        queue<pair<int,int>> q1;
        rel1[1][2] = 0;
        q1.push({1, 2});
        const int dx[3] = {2, 0, 1};
        const int dy[3] = {0, 2, 1};
        while (!q1.empty()) {
            auto [x, y] = q1.front(); q1.pop();
            for (int k = 0; k < 3; ++k) {
                int nx = x + dx[k];
                int ny = y + dy[k];
                if (nx < 1 || nx > n || ny < 1 || ny > n) continue;
                if ((nx + ny) % 2 == 0) continue; // only odd-sum
                if (rel1[nx][ny] != -1) continue;
                int res = ask(x, y, nx, ny);
                rel1[nx][ny] = res ? rel1[x][y] : (rel1[x][y] ^ 1);
                q1.push({nx, ny});
            }
        }
    }

    // BFS2 from (2,1)
    if (n >= 2) {
        queue<pair<int,int>> q2;
        rel2[2][1] = 0;
        q2.push({2, 1});
        const int dx[3] = {2, 0, 1};
        const int dy[3] = {0, 2, 1};
        while (!q2.empty()) {
            auto [x, y] = q2.front(); q2.pop();
            for (int k = 0; k < 3; ++k) {
                int nx = x + dx[k];
                int ny = y + dy[k];
                if (nx < 1 || nx > n || ny < 1 || ny > n) continue;
                if ((nx + ny) % 2 == 0) continue; // only odd-sum
                if (rel2[nx][ny] != -1) continue;
                int res = ask(x, y, nx, ny);
                rel2[nx][ny] = res ? rel2[x][y] : (rel2[x][y] ^ 1);
                q2.push({nx, ny});
            }
        }
    }

    // Find intersection cell of two BFS regions to relate roots
    int px = -1, py = -1;
    for (int i = 1; i <= n && px == -1; ++i) {
        for (int j = 1; j <= n; ++j) {
            if ((i + j) % 2 == 1 && rel1[i][j] != -1 && rel2[i][j] != -1) {
                px = i; py = j;
                break;
            }
        }
    }

    int d = 0;
    if (px != -1) {
        d = rel1[px][py] ^ rel2[px][py]; // value(root1) XOR value(root2)
    }

    // Combine to get relOdd[i][j] = value(i,j) XOR value(root1) for all odd cells
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            if ((i + j) % 2 == 1) {
                if (rel1[i][j] != -1) {
                    relOdd[i][j] = rel1[i][j];
                } else {
                    relOdd[i][j] = rel2[i][j] ^ d;
                }
            }
        }
    }

    // Build two candidate grids: id=0 assumes value(root1)=0, id=1 assumes value(root1)=1
    for (int id = 0; id <= 1; ++id) {
        for (int i = 1; i <= n; ++i) {
            for (int j = 1; j <= n; ++j) {
                if ((i + j) % 2 == 0) {
                    gridVal[id][i][j] = evenVal[i][j];
                } else {
                    gridVal[id][i][j] = relOdd[i][j] ^ id;
                }
            }
        }
    }

    // DP to precompute palindrome-path existence for all pairs for both candidates
    int maxLen = 2 * (n - 1);
    for (int id = 0; id <= 1; ++id) {
        memset(F[id], 0, sizeof(F[id]));
        for (int len = 0; len <= maxLen; ++len) {
            for (int x1 = 1; x1 <= n; ++x1) {
                for (int y1 = 1; y1 <= n; ++y1) {
                    int maxDx = min(len, n - x1);
                    for (int dx = 0; dx <= maxDx; ++dx) {
                        int x2 = x1 + dx;
                        int dy = len - dx;
                        int y2 = y1 + dy;
                        if (y2 < 1 || y2 > n) continue;

                        if (gridVal[id][x1][y1] != gridVal[id][x2][y2]) {
                            F[id][x1][y1][x2][y2] = false;
                            continue;
                        }
                        if (len <= 1) {
                            F[id][x1][y1][x2][y2] = true;
                            continue;
                        }
                        bool ok = false;
                        if (x1 + 1 <= n && x2 - 1 >= 1 && F[id][x1 + 1][y1][x2 - 1][y2]) ok = true;
                        else if (x1 + 1 <= n && y2 - 1 >= 1 && F[id][x1 + 1][y1][x2][y2 - 1]) ok = true;
                        else if (y1 + 1 <= n && x2 - 1 >= 1 && F[id][x1][y1 + 1][x2 - 1][y2]) ok = true;
                        else if (y1 + 1 <= n && y2 - 1 >= 1 && F[id][x1][y1 + 1][x2][y2 - 1]) ok = true;
                        F[id][x1][y1][x2][y2] = ok;
                    }
                }
            }
        }
    }

    // Find a query where candidates differ
    int qx1 = 1, qy1 = 1, qx2 = n, qy2 = n;
    bool found = false;
    for (int x1 = 1; x1 <= n && !found; ++x1) {
        for (int y1 = 1; y1 <= n && !found; ++y1) {
            for (int x2 = x1; x2 <= n && !found; ++x2) {
                for (int y2 = y1; y2 <= n; ++y2) {
                    if (x1 + y1 + 2 > x2 + y2) continue; // must not be adjacent
                    if (F[0][x1][y1][x2][y2] != F[1][x1][y1][x2][y2]) {
                        qx1 = x1; qy1 = y1; qx2 = x2; qy2 = y2;
                        found = true;
                        break;
                    }
                }
            }
        }
    }

    int realAns;
    if (found) {
        realAns = ask(qx1, qy1, qx2, qy2);
    } else {
        // In theory this should never happen; fallback to any valid query
        realAns = F[0][1][1][n][n];
    }

    int root1Value = (realAns == (int)F[0][qx1][qy1][qx2][qy2]) ? 0 : 1;

    // Construct final answer grid using resolved root1Value
    int finalGrid[MAXN + 1][MAXN + 1];
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            if ((i + j) % 2 == 0) {
                finalGrid[i][j] = evenVal[i][j];
            } else {
                finalGrid[i][j] = relOdd[i][j] ^ root1Value;
            }
        }
    }

    // Output final grid
    cout << "!" << '\n';
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            cout << finalGrid[i][j];
        }
        cout << '\n';
    }
    cout.flush();

    return 0;
}