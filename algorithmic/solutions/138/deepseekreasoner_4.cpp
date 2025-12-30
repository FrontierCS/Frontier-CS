#include <bits/stdc++.h>
using namespace std;

int n, m, k;
vector<string> init, target;
struct Preset {
    int np, mp;
    vector<string> mat;
};
vector<Preset> presets;

// character to index (0-61)
int charIdx(char c) {
    if ('a' <= c && c <= 'z') return c - 'a';
    if ('A' <= c && c <= 'Z') return 26 + c - 'A';
    if ('0' <= c && c <= '9') return 52 + c - '0';
    return -1;
}

// for output
vector<tuple<int,int,int>> ops; // op, x, y (1-indexed)

void add_swap(int x1, int y1, int x2, int y2) {
    // ensure (x1,y1) and (x2,y2) are adjacent
    if (x1 == x2) {
        if (y1 < y2) ops.emplace_back(-1, x1, y1); // swap right
        else ops.emplace_back(-2, x1, y1); // swap left
    } else {
        if (x1 < x2) ops.emplace_back(-4, x1, y1); // swap down
        else ops.emplace_back(-3, x1, y1); // swap up
    }
}

// move the tile at (x,y) to (tx,ty) by swapping along a path (Manhattan moves)
// this will disturb other tiles, so only use before fixing any tiles.
void move_tile_by_swaps(vector<string>& grid, int x, int y, int tx, int ty) {
    // move horizontally first, then vertically
    while (y < ty) {
        add_swap(x, y, x, y+1);
        swap(grid[x][y], grid[x][y+1]);
        y++;
    }
    while (y > ty) {
        add_swap(x, y, x, y-1);
        swap(grid[x][y], grid[x][y-1]);
        y--;
    }
    while (x < tx) {
        add_swap(x, y, x+1, y);
        swap(grid[x][y], grid[x+1][y]);
        x++;
    }
    while (x > tx) {
        add_swap(x, y, x-1, y);
        swap(grid[x][y], grid[x-1][y]);
        x--;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    cin >> n >> m >> k;
    init.resize(n);
    for (int i = 0; i < n; i++) cin >> init[i];
    string empty;
    getline(cin, empty); // consume newline
    getline(cin, empty); // empty line
    target.resize(n);
    for (int i = 0; i < n; i++) cin >> target[i];
    presets.resize(k);
    for (int i = 0; i < k; i++) {
        getline(cin, empty); // empty line before preset
        cin >> presets[i].np >> presets[i].mp;
        presets[i].mat.resize(presets[i].np);
        for (int j = 0; j < presets[i].np; j++) cin >> presets[i].mat[j];
    }

    // count characters in initial and target
    vector<int> cnt_init(62, 0), cnt_target(62, 0);
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < m; j++) {
            cnt_init[charIdx(init[i][j])]++;
            cnt_target[charIdx(target[i][j])]++;
        }
    }

    // check if multisets match
    if (cnt_init != cnt_target) {
        cout << "-1\n";
        return 0;
    }

    // we will transform init to target using only swaps (and rotates if needed)
    // first, check if already equal
    if (init == target) {
        cout << "0\n";
        return 0;
    }

    // use a simple method: bring each tile to its target position by swapping
    // we don't care about disturbing already placed tiles, because we will
    // eventually correct them. This may be inefficient but within limits.
    vector<string> cur = init;
    // we'll process each cell in row-major order
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < m; j++) {
            char needed = target[i][j];
            if (cur[i][j] == needed) continue;
            // find needed character in the remaining grid
            bool found = false;
            for (int ii = i; ii < n && !found; ii++) {
                for (int jj = (ii == i ? j+1 : 0); jj < m && !found; jj++) {
                    if (cur[ii][jj] == needed) {
                        // move it to (i,j)
                        move_tile_by_swaps(cur, ii, jj, i, j);
                        found = true;
                        break;
                    }
                }
            }
            // since multisets match, it must be found
        }
    }

    // output operations
    cout << ops.size() << "\n";
    for (auto [op, x, y] : ops) {
        cout << op << " " << x+1 << " " << y+1 << "\n";
    }

    return 0;
}