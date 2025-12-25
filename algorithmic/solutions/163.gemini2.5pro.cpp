#include <iostream>
#include <vector>
#include <numeric>
#include <algorithm>
#include <queue>
#include <map>
#include <set>

using namespace std;

const int N_MAX = 50;
const int M_MAX = 100;

int n, m;
vector<vector<int>> c;
vector<vector<int>> d;
bool adj[M_MAX + 1][M_MAX + 1];
int dr[] = {-1, 1, 0, 0};
int dc[] = {0, 0, -1, 1};

bool is_valid(int r, int c) {
    return r >= 0 && r < n && c >= 0 && c < n;
}

struct State {
    int r, c, mask;
};

struct PathNode {
    int r, c, mask;
};

void solve() {
    cin >> n >> m;
    c.assign(n, vector<int>(n));
    d.assign(n, vector<int>(n, 0));
    for (int i = 0; i <= m; ++i) {
        for (int j = 0; j <= m; ++j) {
            adj[i][j] = false;
        }
    }

    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            cin >> c[i][j];
        }
    }

    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            if (i == 0 || i == n - 1 || j == 0 || j == n - 1) {
                adj[c[i][j]][0] = adj[0][c[i][j]] = true;
            }
            for (int k = 0; k < 4; ++k) {
                int ni = i + dr[k];
                int nj = j + dc[k];
                if (is_valid(ni, nj) && c[i][j] != c[ni][nj]) {
                    adj[c[i][j]][c[ni][nj]] = adj[c[ni][nj]][c[i][j]] = true;
                }
            }
        }
    }

    vector<int> p(m);
    iota(p.begin(), p.end(), 1);
    
    vector<int> deg(m + 1, 0);
    for(int i = 1; i <= m; ++i) {
        for(int j = i + 1; j <= m; ++j) {
            if(adj[i][j]) {
                deg[i]++;
                deg[j]++;
            }
        }
    }
    sort(p.begin(), p.end(), [&](int a, int b){
        return deg[a] > deg[b];
    });

    vector<bool> placed(m + 1, false);

    d[n / 2][n / 2] = p[0];
    placed[p[0]] = true;

    for (int k = 1; k < m; ++k) {
        int current_color = p[k];
        vector<int> N_req, F_forbid;
        for (int i = 0; i < k; ++i) {
            if (adj[current_color][p[i]]) {
                N_req.push_back(p[i]);
            } else {
                F_forbid.push_back(p[i]);
            }
        }

        if (N_req.empty()) {
            int best_r = -1, best_c = -1, max_dist = -1;
            for (int r = 0; r < n; ++r) {
                for (int c = 0; c < n; ++c) {
                    if (d[r][c] == 0) {
                        int min_d = 1e9;
                        for (int pr = 0; pr < n; ++pr) {
                            for (int pc = 0; pc < n; ++pc) {
                                if (d[pr][pc] != 0) {
                                    min_d = min(min_d, abs(r - pr) + abs(c - pc));
                                }
                            }
                        }
                        if (min_d > max_dist) {
                            max_dist = min_d;
                            best_r = r;
                            best_c = c;
                        }
                    }
                }
            }
            if (best_r != -1) {
                d[best_r][best_c] = current_color;
            } else { 
                for(int r=0; r<n; ++r) for(int c=0; c<n; ++c) if(d[r][c] == 0) { d[r][c] = current_color; goto found_cell; }
                found_cell:;
            }
        } else {
            map<int, int> n_map;
            for (size_t i = 0; i < N_req.size(); ++i) {
                n_map[N_req[i]] = i;
            }

            vector<vector<vector<int>>> dist(n, vector<vector<int>>(n, vector<int>(1 << N_req.size(), -1)));
            vector<vector<vector<PathNode>>> parent(n, vector<vector<PathNode>>(n, vector<PathNode>(1 << N_req.size())));
            queue<State> q;

            set<int> f_set(F_forbid.begin(), F_forbid.end());

            for (int r = 0; r < n; ++r) {
                for (int c = 0; c < n; ++c) {
                    if (d[r][c] == 0) {
                        bool is_adj_to_f = false;
                        for (int i = 0; i < 4; ++i) {
                            int nr = r + dr[i], nc = c + dc[i];
                            if (is_valid(nr, nc) && f_set.count(d[nr][nc])) {
                                is_adj_to_f = true;
                                break;
                            }
                        }
                        if (is_adj_to_f) continue;
                        
                        int initial_mask = 0;
                        for (int i = 0; i < 4; ++i) {
                            int nr = r + dr[i], nc = c + dc[i];
                            if (is_valid(nr, nc) && n_map.count(d[nr][nc])) {
                                initial_mask |= (1 << n_map[d[nr][nc]]);
                            }
                        }
                        if (initial_mask > 0) {
                            dist[r][c][initial_mask] = 1;
                            parent[r][c][initial_mask] = {-1, -1, -1};
                            q.push({r, c, initial_mask});
                        }
                    }
                }
            }
            
            State target = {-1, -1, -1};
            int final_mask = (1 << N_req.size()) - 1;

            while (!q.empty()) {
                State curr = q.front();
                q.pop();

                if (curr.mask == final_mask) {
                    target = curr;
                    break;
                }

                for (int i = 0; i < 4; ++i) {
                    int nr = curr.r + dr[i], nc = curr.c + dc[i];
                    if (!is_valid(nr, nc) || d[nr][nc] != 0) continue;

                    bool is_adj_to_f = false;
                    for (int j = 0; j < 4; ++j) {
                        int nnr = nr + dr[j], nnc = nc + dc[j];
                        if (is_valid(nnr, nnc) && f_set.count(d[nnr][nnc])) {
                            is_adj_to_f = true;
                            break;
                        }
                    }
                    if (is_adj_to_f) continue;

                    int new_mask = curr.mask;
                    for (int j = 0; j < 4; ++j) {
                        int nnr = nr + dr[j], nnc = nc + dc[j];
                        if (is_valid(nnr, nnc) && n_map.count(d[nnr][nnc])) {
                            new_mask |= (1 << n_map[d[nnr][nnc]]);
                        }
                    }

                    if (dist[nr][nc][new_mask] == -1) {
                        dist[nr][nc][new_mask] = dist[curr.r][curr.c][curr.mask] + 1;
                        parent[nr][nc][new_mask] = {curr.r, curr.c, curr.mask};
                        q.push({nr, nc, new_mask});
                    }
                }
            }

            if (target.r != -1) {
                State curr = target;
                while (curr.r != -1) {
                    d[curr.r][curr.c] = current_color;
                    PathNode p_node = parent[curr.r][curr.c][curr.mask];
                    curr = {p_node.r, p_node.c, p_node.mask};
                }
            }
        }
        placed[current_color] = true;
    }

    for (int color = 1; color <= m; ++color) {
        if (adj[color][0]) {
            bool on_border = false;
            for(int r=0; r<n && !on_border; ++r) {
                for(int c=0; c<n; ++c) {
                    if(d[r][c] == color && (r==0 || r==n-1 || c==0 || c==n-1)) {
                        on_border = true;
                        break;
                    }
                }
            }
            if(on_border) continue;

            vector<pair<int, int>> q;
            vector<vector<int>> dist(n, vector<int>(n, -1));
            vector<vector<pair<int, int>>> parent(n, vector<pair<int, int>>(n, {-1, -1}));
            
            for (int r = 0; r < n; ++r) {
                for (int c = 0; c < n; ++c) {
                    if (d[r][c] == color) {
                        q.push_back({r, c});
                        dist[r][c] = 0;
                    }
                }
            }

            int head = 0;
            pair<int, int> target = {-1, -1};
            while(head < q.size()){
                pair<int, int> curr = q[head++];
                if ((d[curr.first][curr.second] == 0) && (curr.first == 0 || curr.first == n - 1 || curr.second == 0 || curr.second == n - 1)) {
                    target = curr;
                    break;
                }

                for(int i = 0; i < 4; ++i) {
                    int nr = curr.first + dr[i];
                    int nc = curr.second + dc[i];
                    if(!is_valid(nr, nc)) continue;

                    if(d[nr][nc] == 0 || d[nr][nc] == color) {
                         bool safe = true;
                         if (d[nr][nc] == 0) {
                            for(int j=0; j<4; ++j) {
                                int nnr = nr + dr[j];
                                int nnc = nc + dc[j];
                                if(is_valid(nnr, nnc) && d[nnr][nnc] != 0 && d[nnr][nnc] != color && !adj[color][d[nnr][nnc]]) {
                                    safe = false;
                                    break;
                                }
                            }
                         }
                         if(safe && dist[nr][nc] == -1) {
                            dist[nr][nc] = dist[curr.first][curr.second] + 1;
                            parent[nr][nc] = curr;
                            q.push_back({nr, nc});
                         }
                    }
                }
            }

            if(target.first != -1) {
                pair<int, int> curr = target;
                while(d[curr.first][curr.second] == 0) {
                    d[curr.first][curr.second] = color;
                    curr = parent[curr.first][curr.second];
                }
            }
        }
    }

    for (int i = 0; i < n; ++i) {
        for (int j = 0; j < n; ++j) {
            cout << d[i][j] << (j == n - 1 ? "" : " ");
        }
        cout << endl;
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    solve();
    return 0;
}