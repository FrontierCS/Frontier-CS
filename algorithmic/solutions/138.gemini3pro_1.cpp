#include <iostream>
#include <vector>
#include <string>
#include <map>
#include <cmath>
#include <algorithm>

using namespace std;

int N, M, K;
vector<string> initial_grid;
vector<string> target_grid;
struct Preset {
    int h, w;
    vector<string> grid;
};
vector<Preset> presets;

struct Operation {
    int type; 
    int x, y; 
};
vector<Operation> ans;

vector<string> current_grid;
vector<vector<bool>> locked;

void add_op(int type, int r, int c) {
    ans.push_back({type, r + 1, c + 1});
}

void do_swap(int r1, int c1, int r2, int c2) {
    char tmp = current_grid[r1][c1];
    current_grid[r1][c1] = current_grid[r2][c2];
    current_grid[r2][c2] = tmp;
    
    if (r1 == r2) {
        if (c2 == c1 + 1) add_op(-1, r1, c1); 
        else if (c2 == c1 - 1) add_op(-2, r1, c1); 
    } else {
        if (r2 == r1 + 1) add_op(-4, r1, c1); 
        else if (r2 == r1 - 1) add_op(-3, r1, c1); 
    }
}

void do_preset(int p_idx, int r, int c) {
    add_op(p_idx + 1, r, c);
    const auto& p = presets[p_idx];
    for(int i=0; i<p.h; ++i) {
        for(int j=0; j<p.w; ++j) {
            current_grid[r+i][c+j] = p.grid[i][j];
        }
    }
}

void move_char(int sr, int sc, int tr, int tc) {
    if (sr == tr) {
        while (sc > tc) {
            do_swap(sr, sc, sr, sc-1);
            sc--;
        }
        while (sc < tc) {
             do_swap(sr, sc, sr, sc+1);
             sc++;
        }
    } else {
        while (sc < tc) {
            do_swap(sr, sc, sr, sc+1);
            sc++;
        }
        while (sc > tc) {
            do_swap(sr, sc, sr, sc-1);
            sc--;
        }
        while (sr > tr) {
            do_swap(sr, sc, sr-1, sc);
            sr--;
        }
    }
}

map<char, int> get_counts(bool target, int start_r, int start_c) {
    map<char, int> cnt;
    for(int i=0; i<N; ++i) {
        for(int j=0; j<M; ++j) {
            bool include = false;
            if (i > start_r || (i == start_r && j >= start_c)) include = true;
            
            if (include) {
                if (target) cnt[target_grid[i][j]]++;
                else cnt[current_grid[i][j]]++;
            }
        }
    }
    return cnt;
}

bool can_generate(char c, int r_start, int c_start) {
    for(int k=0; k<K; ++k) {
        bool has_char = false;
        for(auto &row : presets[k].grid) {
            for(char ch : row) if(ch == c) has_char = true;
        }
        if(!has_char) continue;
        
        for(int i=0; i<N; ++i) {
            for(int j=0; j<M; ++j) {
                if (i + presets[k].h > N || j + presets[k].w > M) continue;
                bool top_left_unlocked = (i > r_start) || (i == r_start && j >= c_start);
                if (top_left_unlocked) return true;
            }
        }
    }
    return false;
}

void solve() {
    current_grid = initial_grid;
    locked.assign(N, vector<bool>(M, false));
    
    for(int i=0; i<N; ++i) {
        for(int j=0; j<M; ++j) {
            while(true) {
                map<char, int> needed = get_counts(true, i, j);
                map<char, int> current = get_counts(false, i, j);
                
                char endangered = 0;
                
                for(auto const& [ch, count] : needed) {
                    if (current[ch] < count) {
                        int ni = i, nj = j + 1;
                        if (nj == M) { ni++; nj = 0; }
                        if (!can_generate(ch, ni, nj)) {
                            endangered = ch;
                            break;
                        }
                    }
                }
                
                if (endangered == 0) break; 
                
                int best_p = -1, best_r = -1, best_c = -1;
                for(int k=0; k<K; ++k) {
                    bool has = false;
                    for(auto &s : presets[k].grid) for(char c : s) if(c == endangered) has = true;
                    if(!has) continue;
                    
                    for(int r=0; r<N; ++r) {
                        for(int c=0; c<M; ++c) {
                            if ((r > i || (r == i && c >= j)) && r + presets[k].h <= N && c + presets[k].w <= M) {
                                best_p = k; best_r = r; best_c = c;
                                goto found_preset;
                            }
                        }
                    }
                }
                found_preset:;
                
                if (best_p == -1) {
                    cout << "-1" << endl;
                    return;
                }
                
                current = get_counts(false, i, j); 
                int ph = presets[best_p].h;
                int pw = presets[best_p].w;
                
                vector<pair<int, int>> garbage_spots;
                for(int r=0; r<N; ++r) {
                    for(int c=0; c<M; ++c) {
                        bool is_unlocked = (r > i || (r == i && c >= j));
                        bool inside = (r >= best_r && r < best_r + ph && c >= best_c && c < best_c + pw);
                        if (is_unlocked && !inside) {
                             char ch = current_grid[r][c];
                             if (current[ch] > needed[ch]) {
                                 garbage_spots.push_back({r, c});
                                 current[ch]--; 
                             }
                        }
                    }
                }
                
                current = get_counts(false, i, j);
                int g_idx = 0;
                for(int r=best_r; r < best_r + ph; ++r) {
                    for(int c=best_c; c < best_c + pw; ++c) {
                        char ch = current_grid[r][c];
                        if (current[ch] <= needed[ch]) {
                            if (g_idx < garbage_spots.size()) {
                                pair<int, int> g = garbage_spots[g_idx++];
                                move_char(r, c, g.first, g.second);
                            }
                        } else {
                            current[ch]--; 
                        }
                    }
                }
                
                do_preset(best_p, best_r, best_c);
            }
            
            char req = target_grid[i][j];
            int fr = -1, fc = -1;
            int dist = 1e9;
            
            for(int r=0; r<N; ++r) {
                for(int c=0; c<M; ++c) {
                    if (r > i || (r == i && c >= j)) {
                        if (current_grid[r][c] == req) {
                            int d = abs(r - i) + abs(c - j);
                            if (d < dist) {
                                dist = d; fr = r; fc = c;
                            }
                        }
                    }
                }
            }
            
            if (fr == -1) {
                int best_p = -1, best_r = -1, best_c = -1;
                for(int k=0; k<K; ++k) {
                    bool has = false;
                    for(auto &s : presets[k].grid) for(char c : s) if(c == req) has = true;
                    if(!has) continue;
                    for(int r=0; r<N; ++r) {
                        for(int c=0; c<M; ++c) {
                            if ((r > i || (r == i && c >= j)) && r + presets[k].h <= N && c + presets[k].w <= M) {
                                best_p = k; best_r = r; best_c = c;
                                goto found_req_preset;
                            }
                        }
                    }
                }
                found_req_preset:;
                
                if (best_p == -1) {
                    cout << "-1" << endl;
                    return;
                }
                
                map<char, int> needed = get_counts(true, i, j);
                map<char, int> current = get_counts(false, i, j);
                int ph = presets[best_p].h;
                int pw = presets[best_p].w;
                vector<pair<int, int>> garbage_spots;
                for(int r=0; r<N; ++r) {
                    for(int c=0; c<M; ++c) {
                        bool is_unlocked = (r > i || (r == i && c >= j));
                        bool inside = (r >= best_r && r < best_r + ph && c >= best_c && c < best_c + pw);
                        if (is_unlocked && !inside) {
                             char ch = current_grid[r][c];
                             if (current[ch] > needed[ch]) {
                                 garbage_spots.push_back({r, c});
                                 current[ch]--; 
                             }
                        }
                    }
                }
                current = get_counts(false, i, j);
                int g_idx = 0;
                for(int r=best_r; r < best_r + ph; ++r) {
                    for(int c=best_c; c < best_c + pw; ++c) {
                        char ch = current_grid[r][c];
                        if (current[ch] <= needed[ch]) {
                            if (g_idx < garbage_spots.size()) {
                                pair<int, int> g = garbage_spots[g_idx++];
                                move_char(r, c, g.first, g.second);
                            }
                        } else {
                            current[ch]--;
                        }
                    }
                }
                do_preset(best_p, best_r, best_c);
                
                dist = 1e9;
                for(int r=0; r<N; ++r) {
                    for(int c=0; c<M; ++c) {
                        if (r > i || (r == i && c >= j)) {
                            if (current_grid[r][c] == req) {
                                int d = abs(r - i) + abs(c - j);
                                if (d < dist) {
                                    dist = d; fr = r; fc = c;
                                }
                            }
                        }
                    }
                }
            }
            
            move_char(fr, fc, i, j);
            locked[i][j] = true;
        }
    }
    
    cout << ans.size() << endl;
    for(auto &op : ans) {
        cout << op.type << " " << op.x << " " << op.y << endl;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    if (!(cin >> N >> M >> K)) return 0;
    initial_grid.resize(N);
    for(int i=0; i<N; ++i) cin >> initial_grid[i];
    target_grid.resize(N);
    for(int i=0; i<N; ++i) cin >> target_grid[i];
    presets.resize(K);
    for(int i=0; i<K; ++i) {
        cin >> presets[i].h >> presets[i].w;
        presets[i].grid.resize(presets[i].h);
        for(int j=0; j<presets[i].h; ++j) cin >> presets[i].grid[j];
    }
    
    solve();
    return 0;
}