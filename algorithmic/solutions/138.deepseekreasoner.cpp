#include <bits/stdc++.h>
using namespace std;

const int MAX_TYPES = 62;
const int MAX_OPS = 400000;
const int MAX_PRESET_OPS = 400;

int n, m, k;
vector<string> cur, target;
vector<vector<string>> preset_pat;
vector<int> preset_n, preset_m;
vector<vector<int>> preset_cnt; // count per preset

vector<tuple<int,int,int>> ops; // (op, x, y) 1-indexed

int char2idx(char c) {
    if ('a' <= c && c <= 'z') return c - 'a';
    if ('A' <= c && c <= 'Z') return 26 + c - 'A';
    if ('0' <= c && c <= '9') return 52 + c - '0';
    return -1;
}

char idx2char(int i) {
    if (i < 26) return 'a' + i;
    if (i < 52) return 'A' + (i - 26);
    return '0' + (i - 52);
}

vector<int> count_grid(const vector<string>& g) {
    vector<int> cnt(MAX_TYPES, 0);
    for (int i = 0; i < n; i++) {
        for (int j = 0; j < m; j++) {
            cnt[char2idx(g[i][j])]++;
        }
    }
    return cnt;
}

vector<int> count_preset(const vector<string>& pat) {
    vector<int> cnt(MAX_TYPES, 0);
    for (const string& s : pat) {
        for (char c : s) {
            cnt[char2idx(c)]++;
        }
    }
    return cnt;
}

// move character from (x1,y1) to (x2,y2) using swaps, updates cur and ops
void move_char(int x1, int y1, int x2, int y2) {
    // all coordinates 0-indexed internally
    while (x1 > x2) {
        ops.push_back({-3, x1+1, y1+1}); // swap up
        swap(cur[x1][y1], cur[x1-1][y1]);
        x1--;
    }
    while (x1 < x2) {
        ops.push_back({-4, x1+1, y1+1}); // swap down
        swap(cur[x1][y1], cur[x1+1][y1]);
        x1++;
    }
    while (y1 > y2) {
        ops.push_back({-2, x1+1, y1+1}); // swap left
        swap(cur[x1][y1], cur[x1][y1-1]);
        y1--;
    }
    while (y1 < y2) {
        ops.push_back({-1, x1+1, y1+1}); // swap right
        swap(cur[x1][y1], cur[x1][y1+1]);
        y1++;
    }
}

// set block at top-left (bx,by) 1-indexed, size (np,mp) to desired pattern des (np x mp)
void set_block(int bx, int by, int np, int mp, const vector<string>& des) {
    // convert to 0-index
    int x0 = bx-1, y0 = by-1;
    int max_iter = 10;
    for (int iter = 0; iter < max_iter; iter++) {
        bool changed = false;
        for (int i = 0; i < np; i++) {
            for (int j = 0; j < mp; j++) {
                int x = x0 + i;
                int y = y0 + j;
                if (cur[x][y] != des[i][j]) {
                    // find nearest cell with desired character
                    int best_dist = 1e9;
                    int best_x = -1, best_y = -1;
                    for (int xx = 0; xx < n; xx++) {
                        for (int yy = 0; yy < m; yy++) {
                            if (cur[xx][yy] == des[i][j]) {
                                int dist = abs(xx - x) + abs(yy - y);
                                if (dist < best_dist) {
                                    best_dist = dist;
                                    best_x = xx;
                                    best_y = yy;
                                }
                            }
                        }
                    }
                    if (best_x != -1) {
                        move_char(best_x, best_y, x, y);
                        changed = true;
                    }
                }
            }
        }
        // check if block matches
        bool match = true;
        for (int i = 0; i < np; i++) {
            for (int j = 0; j < mp; j++) {
                if (cur[x0+i][y0+j] != des[i][j]) {
                    match = false;
                    break;
                }
            }
            if (!match) break;
        }
        if (match) break;
        if (!changed) break;
    }
}

// BFS to find sequence of presets to reach target counts
bool find_preset_sequence(const vector<int>& init_cnt, const vector<int>& tar_cnt,
                          vector<int>& preset_seq) {
    // state: vector<int> of length MAX_TYPES
    map<vector<int>, pair<vector<int>, int>> prev; // prev state and preset index used
    queue<vector<int>> q;
    q.push(init_cnt);
    prev[init_cnt] = {init_cnt, -1};

    while (!