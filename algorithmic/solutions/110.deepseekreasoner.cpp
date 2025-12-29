#include <bits/stdc++.h>
using namespace std;

const int ROWS = 8;
const int COLS = 14;
const int MAX_TEST = 200000;

using Grid = vector<string>;

vector<pair<int,int>> dirs = {{-1,-1},{-1,0},{-1,1},{0,-1},{0,1},{1,-1},{1,0},{1,1}};
vector<pair<int,int>> neighbors[ROWS][COLS];

void precompute_neighbors() {
    for (int i=0; i<ROWS; i++) {
        for (int j=0; j<COLS; j++) {
            for (auto d : dirs) {
                int ni = i + d.first;
                int nj = j + d.second;
                if (ni>=0 && ni<ROWS && nj>=0 && nj<COLS) {
                    neighbors[i][j].push_back({ni, nj});
                }
            }
        }
    }
}

bool canRead(const Grid& grid, const string& s) {
    int n = s.size();
    bool cur[ROWS][COLS] = {false};
    for (int i=0; i<ROWS; i++)
        for (int j=0; j<COLS; j++)
            if (grid[i][j] == s[0])
                cur[i][j] = true;

    for (int idx=1; idx<n; idx++) {
        bool nxt[ROWS][COLS] = {false};
        for (int i=0; i<ROWS; i++) {
            for (int j=0; j<COLS; j++) {
                if (!cur[i][j]) continue;
                for (auto& nb : neighbors[i][j]) {
                    int ni = nb.first, nj = nb.second;
                    if (grid[ni][nj] == s[idx])
                        nxt[ni][nj] = true;
                }
            }
        }
        bool any = false;
        for (int i=0; i<ROWS && !any; i++)
            for (int j=0; j<COLS && !any; j++)
                if (nxt[i][j]) any = true;
        if (!any) return false;
        memcpy(cur, nxt, sizeof(cur));
    }
    return true;
}

int compute_X(const Grid& grid, int limit) {
    for (int n=1; n<=limit; n++) {
        if (!canRead(grid, to_string(n)))
            return n-1;
    }
    return limit;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(nullptr);

    precompute_neighbors();
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());
    uniform_int_distribution<int> dist(0,9);

    Grid best_grid(ROWS, string(COLS, '0'));
    int best_X = 0;
    auto start = chrono::steady_clock::now();

    while (true) {
        auto now = chrono::steady_clock::now();
        chrono::duration<double> elapsed = now - start;
        if (elapsed.count() > 58.0) break;

        Grid grid(ROWS, string(COLS, '0'));
        for (int i=0; i<ROWS; i++)
            for (int j=0; j<COLS; j++)
                grid[i][j] = '0' + dist(rng);

        int X = compute_X(grid, MAX_TEST);
        if (X > best_X) {
            best_X = X;
            best_grid = grid;
        }
    }

    for (int i=0; i<ROWS; i++)
        cout << best_grid[i] << '\n';

    return 0;
}