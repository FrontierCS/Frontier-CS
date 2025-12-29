#include <bits/stdc++.h>
using namespace std;

const int N = 50;
const int M = 100;
int original[N][N];
bool must0[M+1] = {false};
set<int> adj[M+1];   // adjacency including 0 if applicable

int grid10[10][10];  // assignment of colors to 10x10 macro cells

int output[N][N];

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int n, m;
    cin >> n >> m;   // n=50, m=100

    for (int i = 0; i < n; ++i)
        for (int j = 0; j < n; ++j)
            cin >> original[i][j];

    // compute adjacency and must0
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            int c = original[i][j];
            const int di[] = {-1, 1, 0, 0};
            const int dj[] = {0, 0, -1, 1};
            for (int k = 0; k < 4; ++k) {
                int ni = i + di[k], nj = j + dj[k];
                if (ni < 0 || ni >= n || nj < 0 || nj >= n) {
                    must0[c] = true;
                } else {
                    int nc = original[ni][nj];
                    if (nc != c) {
                        adj[c].insert(nc);
                        adj[nc].insert(c);
                    }
                }
            }
        }
    }

    // remove 0 from adj sets (if inserted by mistake, but we never insert 0)
    for (int c = 1; c <= m; ++c) {
        adj[c].erase(0);
    }

    // initial random assignment of colors to 10x10 grid
    vector<int> colors(m);
    iota(colors.begin(), colors.end(), 1);
    random_shuffle(colors.begin(), colors.end());
    for (int idx = 0; idx < m; ++idx) {
        int i = idx / 10, j = idx % 10;
        grid10[i][j] = colors[idx];
    }

    // penalty function
    auto compute_penalty = [&]() {
        int penalty = 0;
        map<int, pair<int,int>> pos;
        for (int i = 0; i < 10; ++i)
            for (int j = 0; j < 10; ++j)
                pos[grid10[i][j]] = {i, j};

        // must0 colors should be on boundary
        for (int c = 1; c <= m; ++c) {
            auto [i, j] = pos[c];
            if (must0[c]) {
                if (i > 0 && i < 9 && j > 0 && j < 9)
                    penalty += 1000;
            } else {
                // must not be adjacent to 0 → all macro neighbours must be adjacent in graph
                const vector<pair<int,int>> dirs = {{-1,0},{1,0},{0,-1},{0,1}};
                for (auto [di, dj] : dirs) {
                    int ni = i + di, nj = j + dj;
                    if (ni >= 0 && ni < 10 && nj >= 0 && nj < 10) {
                        int d = grid10[ni][nj];
                        if (adj[c].find(d) == adj[c].end())
                            penalty += 100;
                    }
                }
            }
        }

        // edges in the graph should be adjacent in macro grid
        for (int c = 1; c <= m; ++c) {
            for (int d : adj[c]) {
                if (d <= c || d == 0) continue;
                auto [i1, j1] = pos[c];
                auto [i2, j2] = pos[d];
                if (abs(i1 - i2) + abs(j1 - j2) != 1)
                    penalty += 10;
            }
        }
        return penalty;
    };

    // hill climbing with random swaps
    int current_penalty = compute_penalty();
    for (int iter = 0; iter < 50000; ++iter) {
        int i1 = rand() % 10, j1 = rand() % 10;
        int i2 = rand() % 10, j2 = rand() % 10;
        if (i1 == i2 && j1 == j2) continue;
        swap(grid10[i1][j1], grid10[i2][j2]);
        int new_penalty = compute_penalty();
        if (new_penalty < current_penalty) {
            current_penalty = new_penalty;
        } else {
            swap(grid10[i1][j1], grid10[i2][j2]); // revert
        }
    }

    // build output grid
    memset(output, 0, sizeof(output));
    map<int, pair<int,int>> pos;
    for (int i = 0; i < 10; ++i)
        for (int j = 0; j < 10; ++j)
            pos[grid10[i][j]] = {i, j};

    // place 3x3 blocks for each color
    for (int c = 1; c <= m; ++c) {
        auto [I, J] = pos[c];
        int r0 = 5 + 4 * I;
        int c0 = 5 + 4 * J;
        for (int dr = 0; dr < 3; ++dr)
            for (int dc = 0; dc < 3; ++dc)
                output[r0 + dr][c0 + dc] = c;
    }

    // create bridges for adjacent colors that are macro neighbours
    for (int I = 0; I < 10; ++I) {
        for (int J = 0; J < 10; ++J) {
            int c = grid10[I][J];
            int r0 = 5 + 4 * I, c0 = 5 + 4 * J;

            // right neighbour
            if (J + 1 < 10) {
                int d = grid10[I][J+1];
                if (adj[c].find(d) != adj[c].end()) {
                    int r = r0 + 1;
                    int gap_col = c0 + 3;
                    output[r][gap_col] = c;
                }
            }
            // down neighbour
            if (I + 1 < 10) {
                int d = grid10[I+1][J];
                if (adj[c].find(d) != adj[c].end()) {
                    int col = c0 + 1;
                    int gap_row = r0 + 3;
                    output[gap_row][col] = c;
                }
            }
        }
    }

    // output
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            cout << output[i][j];
            if (j < n-1) cout << ' ';
        }
        cout << '\n';
    }

    return 0;
}