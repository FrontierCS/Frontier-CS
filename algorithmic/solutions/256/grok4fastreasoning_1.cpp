#include <bits/stdc++.h>
using namespace std;

int main() {
    int n;
    cin >> n;
    vector<vector<int>> grid(n + 1, vector<int>(n + 1, -1));
    grid[1][1] = 1;

    auto ask = [&](int x1, int y1, int x2, int y2) {
        cout << "? " << x1 << " " << y1 << " " << x2 << " " << y2 << endl;
        cout.flush();
        int res;
        cin >> res;
        if (res == -1) exit(0);
        return res;
    };

    // Set even anti-diagonals
    for (int s = 4; s <= 2 * n; s += 2) {
        for (int x = max(1, s - n); x <= min(n, s - 1); ++x) {
            int y = s - x;
            if (y < 1 || y > n) continue;
            bool setted = false;
            // Try horizontal pred
            int px = x, py = y - 2;
            if (py >= 1 && grid[px][py] != -1) {
                int eq = ask(px, py, x, y);
                grid[x][y] = (eq == 1 ? grid[px][py] : 1 - grid[px][py]);
                setted = true;
            }
            if (!setted) {
                // Try vertical pred
                px = x - 2, py = y;
                if (px >= 1 && grid[px][py] != -1) {
                    int eq = ask(px, py, x, y);
                    grid[x][y] = (eq == 1 ? grid[px][py] : 1 - grid[px][py]);
                    setted = true;
                }
            }
            if (!setted) {
                // Try diagonal pred
                px = x - 1, py = y - 1;
                if (px >= 1 && py >= 1 && grid[px][py] != -1) {
                    int eq = ask(px, py, x, y);
                    grid[x][y] = (eq == 1 ? grid[px][py] : 1 - grid[px][py]);
                    setted = true;
                }
            }
            assert(setted);
        }
    }

    // Now odds
    vector<pair<int, int>> odd_cells;
    vector<vector<int>> cell_id(n + 1, vector<int>(n + 1, -1));
    int idx = 0;
    for (int s = 3; s <= 2 * n - 1; s += 2) {
        for (int x = max(1, s - n); x <= min(n, s - 1); ++x) {
            int y = s - x;
            if (y >= 1 && y <= n) {
                odd_cells.emplace_back(x, y);
                cell_id[x][y] = idx++;
            }
        }
    }
    int m = odd_cells.size();
    vector<int> par(m), rel(m, 0), rnk(m, 0);
    for (int i = 0; i < m; ++i) par[i] = i;

    auto find = [&](auto&& self, int ii) -> int {
        if (par[ii] != ii) {
            int p = self(self, par[ii]);
            rel[ii] = rel[ii] ^ rel[par[ii]];
            par[ii] = p;
        }
        return par[ii];
    };

    auto union_sets = [&](int i, int j, int eq) {
        int xor_val = 1 - eq;
        int pi = find(find, i);
        int ri = rel[i];
        int pj = find(find, j);
        int rj = rel[j];
        if (pi == pj) {
            if ((ri ^ rj) != xor_val) {
                // inconsistency, shouldn't happen
                assert(false);
            }
            return;
        }
        if (rnk[pi] < rnk[pj]) {
            swap(pi, pj);
            swap(ri, rj);
        }
        par[pj] = pi;
        rel[pj] = ri ^ rj ^ xor_val;
        if (rnk[pi] == rnk[pj]) ++rnk[pi];
    };

    // Build connections for odds
    for (int k = 0; k < m; ++k) {
        auto [x, y] = odd_cells[k];
        vector<pair<int, int>> preds;
        // horizontal
        int px = x, py = y - 2;
        if (py >= 1 && cell_id[px][py] != -1) preds.emplace_back(px, py);
        // vertical
        px = x - 2, py = y;
        if (px >= 1 && cell_id[px][py] != -1) preds.emplace_back(px, py);
        // diagonal
        px = x - 1, py = y - 1;
        if (px >= 1 && py >= 1 && cell_id[px][py] != -1) preds.emplace_back(px, py);
        for (auto [pxx, pyy] : preds) {
            int ii = cell_id[x][y];
            int jj = cell_id[pxx][pyy];
            int eqq = ask(pxx, pyy, x, y);
            union_sets(ii, jj, eqq);
        }
    }

    // Compress all
    for (int i = 0; i < m; ++i) find(find, i);

    // get_parity
    auto get_parity = [&](int xx, int yy) -> int {
        int i = cell_id[xx][yy];
        int refi = cell_id[1][2];
        return rel[i] ^ rel[refi];
    };

    auto get_odd_val = [&](int xx, int yy, int ref_val) -> int {
        int diff = get_parity(xx, yy);
        return (diff == 0 ? ref_val : 1 - ref_val);
    };

    // Now find a good query
    int chosen_x1 = -1, chosen_y1 = -1, chosen_x2 = -1, chosen_y2 = -1;
    int pred_for_0 = -1, pred_for_1 = -1;
    bool found_good = false;
    for (int x2 = 1; x2 <= n && !found_good; ++x2) {
        for (int y2 = 1; y2 <= n && !found_good; ++y2) {
            if (cell_id[x2][y2] == -1) continue;
            for (int ddx = 0; ddx <= 3; ++ddx) {
                int ddy = 3 - ddx;
                int x1 = x2 - ddx;
                int y1 = y2 - ddy;
                if (x1 < 1 || y1 < 1) continue;
                if (grid[x1][y1] == -1) continue;
                // compute for ref 0 and 1
                auto has_good_path = [&](int ref_val) -> bool {
                    int gstart = grid[x1][y1];
                    int gend = get_odd_val(x2, y2, ref_val);
                    if (gstart != gend) return false;
                    // rec to check exists
                    function<bool(int cx, int cy, int step, int dused, int p2x, int p2y, int p3x, int p3y)> checkk = [&](int cx, int cy, int step, int dused, int p2x, int p2y, int p3x, int p3y) -> bool {
                        if (step == 3) {
                            if (cx == x2 && cy == y2 && dused == ddx) {
                                int go2 = get_odd_val(p2x, p2y, ref_val);
                                int ge3 = grid[p3x][p3y];
                                return go2 == ge3;
                            }
                            return false;
                        }
                        // right
                        {
                            int nx = cx, ny = cy + 1;
                            if (ny <= n) {
                                int np2x = (step == 0 ? nx : p2x);
                                int np2y = (step == 0 ? ny : p2y);
                                int np3x = (step == 1 ? nx : p3x);
                                int np3y = (step == 1 ? ny : p3y);
                                if (checkk(nx, ny, step + 1, dused, np2x, np2y, np3x, np3y)) return true;
                            }
                        }
                        // down
                        {
                            int nx = cx + 1, ny = cy;
                            if (nx <= n) {
                                int np2x = (step == 0 ? nx : p2x);
                                int np2y = (step == 0 ? ny : p2y);
                                int np3x = (step == 1 ? nx : p3x);
                                int np3y = (step == 1 ? ny : p3y);
                                if (checkk(nx, ny, step + 1, dused + 1, np2x, np2y, np3x, np3y)) return true;
                            }
                        }
                        return false;
                    };
                    return checkk(x1, y1, 0, 0, 0, 0, 0, 0);
                };
                bool p0 = has_good_path(0);
                bool p1 = has_good_path(1);
                if (p0 != p1) {
                    chosen_x1 = x1;
                    chosen_y1 = y1;
                    chosen_x2 = x2;
                    chosen_y2 = y2;
                    pred_for_0 = p0 ? 1 : 0;
                    pred_for_1 = p1 ? 1 : 0;
                    found_good = true;
                    break;
                }
            }
        }
    }
    assert(found_good);

    // Ask the good query
    int actual = ask(chosen_x1, chosen_y1, chosen_x2, chosen_y2);

    int chosen_ref;
    if (actual == pred_for_0) {
        chosen_ref = 0;
    } else {
        chosen_ref = 1;
    }

    // Set all odds
    for (auto [xx, yy] : odd_cells) {
        int diff = get_parity(xx, yy);
        grid[xx][yy] = (diff == 0 ? chosen_ref : 1 - chosen_ref);
    }

    // Output
    cout << "!" << endl;
    for (int i = 1; i <= n; ++i) {
        for (int j = 1; j <= n; ++j) {
            cout << grid[i][j];
        }
        cout << endl;
    }
    cout.flush();
    return 0;
}