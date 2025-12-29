#include <bits/stdc++.h>
using namespace std;

int n, m, k;
vector<string> init, target;
vector<vector<string>> presets;
vector<pair<int, int>> preset_sizes;

// Character mapping: 'a'-'z', 'A'-'Z', '0'-'9' -> 0..61
int char_idx(char c) {
    if ('a' <= c && c <= 'z') return c - 'a';
    if ('A' <= c && c <= 'Z') return 26 + c - 'A';
    return 52 + c - '0';
}
char idx_char(int i) {
    if (i < 26) return 'a' + i;
    if (i < 52) return 'A' + i - 26;
    return '0' + i - 52;
}

vector<int> get_counts(const vector<string>& grid) {
    vector<int> cnt(62, 0);
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < m; ++j)
            cnt[char_idx(grid[i][j])]++;
    return cnt;
}

vector<int> get_preset_counts(int idx) {
    vector<int> cnt(62, 0);
    for (const string& s : presets[idx])
        for (char c : s)
            cnt[char_idx(c)]++;
    return cnt;
}

struct Operation {
    int op, x, y;
};

vector<Operation> moves;

// Current grid (0-indexed internally, but moves use 1-indexed)
vector<string> cur_grid;

void swap_down(int x, int y) { // x from 0 to n-2
    moves.push_back({-4, x+1, y+1});
    swap(cur_grid[x][y], cur_grid[x+1][y]);
}
void swap_up(int x, int y) { // x from 1 to n-1
    moves.push_back({-3, x+1, y+1});
    swap(cur_grid[x][y], cur_grid[x-1][y]);
}
void swap_right(int x, int y) { // y from 0 to m-2
    moves.push_back({-1, x+1, y+1});
    swap(cur_grid[x][y], cur_grid[x][y+1]);
}
void swap_left(int x, int y) { // y from 1 to m-1
    moves.push_back({-2, x+1, y+1});
    swap(cur_grid[x][y], cur_grid[x][y-1]);
}

void move_tile(int sx, int sy, int dx, int dy) {
    // move tile from (sx,sy) to (dx,dy) by Manhattan path
    while (sx < dx) {
        swap_down(sx, sy);
        sx++;
    }
    while (sx > dx) {
        swap_up(sx, sy);
        sx--;
    }
    while (sy < dy) {
        swap_right(sx, sy);
        sy++;
    }
    while (sy > dy) {
        swap_left(sx, sy);
        sy--;
    }
}

void apply_preset(int idx, int x, int y) {
    moves.push_back({idx+1, x+1, y+1});
    int h = preset_sizes[idx].first;
    int w = preset_sizes[idx].second;
    for (int i = 0; i < h; ++i)
        for (int j = 0; j < w; ++j)
            cur_grid[x+i][y+j] = presets[idx][i][j];
}

bool greedy_multiset(vector<int>& init_cnt, vector<int>& target_cnt,
                     vector<vector<int>>& preset_cnts, vector<int>& preset_sz,
                     vector<pair<int, vector<int>>>& sequence) {
    vector<int> cur = init_cnt;
    int total_cells = n * m;
    for (int step = 0; step < 400; ++step) {
        if (cur == target_cnt) return true;
        int best_dist = INT_MAX, best_p = -1;
        vector<int> best_removal(62, 0);
        for (int p = 0; p < k; ++p) {
            int sz = preset_sz[p];
            // choose removal: characters with highest surplus first
            vector<pair<int, int>> surplus;
            for (int c = 0; c < 62; ++c)
                if (cur[c] > 0)
                    surplus.emplace_back(cur[c] - target_cnt[c], c);
            sort(surplus.begin(), surplus.end(), greater<pair<int,int>>());
            vector<int> removal(62, 0);
            int rem = sz;
            for (auto& [surp, c] : surplus) {
                if (rem == 0) break;
                int take = min(cur[c], rem);
                removal[c] = take;
                rem -= take;
            }
            if (rem > 0) continue; // shouldn't happen
            // compute new counts
            vector<int> new_cnt(62, 0);
            int dist = 0;
            for (int c = 0; c < 62; ++c) {
                new_cnt[c] = cur[c] - removal[c] + preset_cnts[p][c];
                dist += abs(new_cnt[c] - target_cnt[c]);
            }
            if (dist < best_dist) {
                best_dist = dist;
                best_p = p;
                best_removal = removal;
            }
        }
        if (best_p == -1) return false;
        // apply
        sequence.emplace_back(best_p, best_removal);
        for (int c = 0; c < 62; ++c)
            cur[c] = cur[c] - best_removal[c] + preset_cnts[best_p][c];
    }
    return cur == target_cnt;
}

// return list of cells in block (top-left x,y, height h, width w)
vector<pair<int,int>> block_cells(int x, int y, int h, int w) {
    vector<pair<int,int>> res;
    for (int i = 0; i < h; ++i)
        for (int j = 0; j < w; ++j)
            res.emplace_back(x+i, y+j);
    return res;
}

// adjust block at (x,y) with size (h,w) to have multiset R
void adjust_block(int x, int y, int h, int w, const vector<int>& R) {
    vector<pair<int,int>> cells = block_cells(x, y, h, w);
    vector<int> need = R;
    vector<pair<int,int>> excess_pos;
    // first pass: mark excess cells
    for (auto [i,j] : cells) {
        int c = char_idx(cur_grid[i][j]);
        if (need[c] > 0) {
            need[c]--;
        } else {
            excess_pos.emplace_back(i, j);
        }
    }
    // now need contains characters still needed
    // move excess cells to first row, rightmost columns within block
    int bx = x, by = y;
    // sort excess positions by row descending, then column ascending
    sort(excess_pos.begin(), excess_pos.end(), [](const pair<int,int>& a, const pair<int,int>& b) {
        if (a.first != b.first) return a.first > b.first;
        return a.second < b.second;
    });
    // target positions in first row, from right to left
    vector<pair<int,int>> target_pos;
    int row0 = bx;
    int col_start = by + w - 1;
    for (size_t idx = 0; idx < excess_pos.size(); ++idx) {
        int col = col_start - idx;
        target_pos.emplace_back(row0, col);
    }
    // move each excess cell to its target position within block (using swaps only within block)
    for (size_t idx = 0; idx < excess_pos.size(); ++idx) {
        auto [si, sj] = excess_pos[idx];
        auto [ti, tj] = target_pos[idx];
        // move up to same row
        while (si > ti) {
            swap_up(si, sj);
            si--;
        }
        while (si < ti) {
            swap_down(si, sj);
            si++;
        }
        // move horizontally
        while (sj < tj) {
            swap_right(si, sj);
            sj++;
        }
        while (sj > tj) {
            swap_left(si, sj);
            sj--;
        }
    }
    // now excess cells are at target_pos (first row, rightmost columns)
    // for each needed character, bring from outside to adjacent right cell and swap in
    for (int c = 0; c < 62; ++c) {
        while (need[c] > 0) {
            // find outside cell with character c
            int ox = -1, oy = -1;
            for (int i = 0; i < n; ++i) {
                for (int j = 0; j < m; ++j) {
                    if (i >= bx && i < bx+h && j >= by && j < by+w) continue; // inside block
                    if (char_idx(cur_grid[i][j]) == c) {
                        ox = i; oy = j;
                        break;
                    }
                }
                if (ox != -1) break;
            }
            if (ox == -1) {
                // should not happen because multiset matches
                break;
            }
            // take the rightmost excess cell (which is at target_pos.back())
            auto [dst_i, dst_j] = target_pos.back();
            target_pos.pop_back();
            // move ox,oy to (dst_i, dst_j+1) if possible, else to adjacent outside cell
            int adj_i = dst_i, adj_j = dst_j+1;
            if (adj_j >= by+w) adj_j = dst_j-1; // if right is outside, else left
            if (adj_j < by) adj_j = dst_j+1; // ensure outside
            // move the character from (ox,oy) to (adj_i, adj_j)
            move_tile(ox, oy, adj_i, adj_j);
            // now swap with the excess cell
            if (adj_j == dst_j+1) {
                swap_left(dst_i, dst_j+1); // swap (dst_i, dst_j) and (dst_i, dst_j+1)
            } else {
                swap_right(dst_i, dst_j-1); // swap (dst_i, dst_j) and (dst_i, dst_j-1)
            }
            need[c]--;
        }
    }
}

void permute_to_target() {
    // permute current grid to target using swaps
    // for each cell in row-major order, if not correct, find correct character and bring it
    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < m; ++j) {
            char needed = target[i][j];
            if (cur_grid[i][j] == needed) continue;
            // find needed character in the grid at position > (i,j) in row-major order
            int found_i = -1, found_j = -1;
            for (int ii = i; ii < n; ++ii) {
                int start_j = (ii == i) ? j+1 : 0;
                for (int jj = start_j; jj < m; ++jj) {
                    if (cur_grid[ii][jj] == needed) {
                        found_i = ii; found_j = jj;
                        break;
                    }
                }
                if (found_i != -1) break;
            }
            // move found character to (i,j)
            move_tile(found_i, found_j, i, j);
        }
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    cin >> n >> m >> k;
    init.resize(n);
    for (int i = 0; i < n; ++i) cin >> init[i];
    string empty;
    getline(cin, empty); // consume newline
    getline(cin, empty); // empty line
    target.resize(n);
    for (int i = 0; i < n; ++i) cin >> target[i];
    presets.resize(k);
    preset_sizes.resize(k);
    for (int p = 0; p < k; ++p) {
        getline(cin, empty); // empty line
        int np, mp;
        cin >> np >> mp;
        preset_sizes[p] = {np, mp};
        presets[p].resize(np);
        for (int i = 0; i < np; ++i) cin >> presets[p][i];
    }

    // Check if every character in target appears in initial or any preset
    vector<bool> char_present(62, false);
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < m; ++j)
            char_present[char_idx(init[i][j])] = true;
    for (int p = 0; p < k; ++p)
        for (const string& s : presets[p])
            for (char c : s)
                char_present[char_idx(c)] = true;
    for (int i = 0; i < n; ++i)
        for (int j = 0; j < m; ++j)
            if (!char_present[char_idx(target[i][j])]) {
                cout << "-1\n";
                return 0;
            }

    vector<int> init_cnt = get_counts(init);
    vector<int> target_cnt = get_counts(target);
    vector<vector<int>> preset_cnts(k);
    vector<int> preset_sz(k);
    for (int p = 0; p < k; ++p) {
        preset_cnts[p] = get_preset_counts(p);
        preset_sz[p] = preset_sizes[p].first * preset_sizes[p].second;
    }

    vector<pair<int, vector<int>>> seq; // preset index, removal counts
    if (!greedy_multiset(init_cnt, target_cnt, preset_cnts, preset_sz, seq)) {
        cout << "-1\n";
        return 0;
    }

    // Simulate
    cur_grid = init;
    moves.clear();

    for (auto& [p_idx, removal] : seq) {
        int h = preset_sizes[p_idx].first;
        int w = preset_sizes[p_idx].second;
        // choose position (x,y) with minimal mismatch
        int best_x = 0, best_y = 0, best_miss = INT_MAX;
        for (int x = 0; x <= n - h; ++x) {
            for (int y = 0; y <= m - w; ++y) {
                vector<int> block_cnt(62, 0);
                for (int i = x; i < x+h; ++i)
                    for (int j = y; j < y+w; ++j)
                        block_cnt[char_idx(cur_grid[i][j])]++;
                int miss = 0;
                for (int c = 0; c < 62; ++c)
                    miss += max(0, removal[c] - block_cnt[c]);
                if (miss < best_miss) {
                    best_miss = miss;
                    best_x = x;
                    best_y = y;
                }
            }
        }
        // adjust block to have multiset removal
        adjust_block(best_x, best_y, h, w, removal);
        // apply preset
        apply_preset(p_idx, best_x, best_y);
    }

    // finally permute to target
    permute_to_target();

    // verify (optional)
    if (cur_grid != target) {
        cout << "-1\n";
        return 0;
    }

    // output moves
    cout << moves.size() << "\n";
    for (auto& op : moves)
        cout << op.op << " " << op.x << " " << op.y << "\n";

    return 0;
}