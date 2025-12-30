#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <tuple>
#include <map>
#include <algorithm>
#include <vector>

using namespace std;

const int N = 20;
const int M = 40;
const int INF = 1e9;

int dr[] = {-1, 1, 0, 0}; // U, D, L, R
int dc[] = {0, 0, -1, 1};
char d_char[] = {'U', 'D', 'L', 'R'};

struct State {
    int cost, r, c, mask;

    bool operator>(const State& other) const {
        return cost > other.cost;
    }
};

struct ParentInfo {
    int r, c, mask;
    char action, dir;
};

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n_in, m_in;
    cin >> n_in >> m_in;

    vector<pair<int, int>> targets(M);
    for (int i = 0; i < M; ++i) {
        cin >> targets[i].first >> targets[i].second;
    }

    pair<int, int> current_pos = targets[0];
    vector<vector<bool>> blocks(N, vector<bool>(N, false));
    vector<pair<char, char>> solution;

    for (int k = 1; k < M; ++k) {
        pair<int, int> target_pos = targets[k];

        vector<pair<int, int>> stoppers(4);
        stoppers[0] = {target_pos.first - 1, target_pos.second}; // U
        stoppers[1] = {target_pos.first + 1, target_pos.second}; // D
        stoppers[2] = {target_pos.first, target_pos.second - 1}; // L
        stoppers[3] = {target_pos.first, target_pos.second + 1}; // R
        
        vector<bool> is_stopper_valid(4, false);
        for(int i = 0; i < 4; ++i) {
            if (stoppers[i].first >= 0 && stoppers[i].first < N && stoppers[i].second >= 0 && stoppers[i].second < N) {
                if (!blocks[stoppers[i].first][stoppers[i].second]) {
                    is_stopper_valid[i] = true;
                }
            }
        }

        vector<vector<vector<int>>> dist(N, vector<vector<int>>(N, vector<int>(16, INF)));
        vector<vector<vector<ParentInfo>>> parent(N, vector<vector<ParentInfo>>(N, vector<ParentInfo>(16)));
        priority_queue<State, vector<State>, greater<State>> pq;

        dist[current_pos.first][current_pos.second][0] = 0;
        pq.push({0, current_pos.first, current_pos.second, 0});

        int min_total_cost = INF;
        int best_mask = -1;

        auto is_blocked = [&](int r, int c, int mask) {
            if (r < 0 || r >= N || c < 0 || c >= N) return true;
            if (blocks[r][c]) return true;
            for (int i = 0; i < 4; ++i) {
                if (((mask >> i) & 1) && is_stopper_valid[i] && stoppers[i].first == r && stoppers[i].second == c) {
                    return true;
                }
            }
            return false;
        };
        
        while (!pq.empty()) {
            auto [cost, r, c, mask] = pq.top();
            pq.pop();

            if (cost > dist[r][c][mask]) {
                continue;
            }

            if (r == target_pos.first && c == target_pos.second) {
                int cleanup_cost = 0;
                for (int i = 0; i < 4; ++i) {
                    if ((mask >> i) & 1) {
                        cleanup_cost += 3; // Estimated cleanup cost
                    }
                }
                if (cost + cleanup_cost < min_total_cost) {
                    min_total_cost = cost + cleanup_cost;
                    best_mask = mask;
                }
            }
            
            // Move
            for (int i = 0; i < 4; ++i) {
                int nr = r + dr[i];
                int nc = c + dc[i];
                if (!is_blocked(nr, nc, mask)) {
                    if (cost + 1 < dist[nr][nc][mask]) {
                        dist[nr][nc][mask] = cost + 1;
                        pq.push({cost + 1, nr, nc, mask});
                        parent[nr][nc][mask] = {r, c, mask, 'M', d_char[i]};
                    }
                }
            }

            // Slide
            for (int i = 0; i < 4; ++i) {
                int sr = r, sc = c;
                while (true) {
                    int nsr = sr + dr[i];
                    int nsc = sc + dc[i];
                    if (is_blocked(nsr, nsc, mask)) break;
                    sr = nsr;
                    sc = nsc;
                }
                if (sr != r || sc != c) {
                     if (cost + 1 < dist[sr][sc][mask]) {
                        dist[sr][sc][mask] = cost + 1;
                        pq.push({cost + 1, sr, sc, mask});
                        parent[sr][sc][mask] = {r, c, mask, 'S', d_char[i]};
                    }
                }
            }

            // Alter
            for (int i = 0; i < 4; ++i) {
                if (!((mask >> i) & 1) && is_stopper_valid[i]) {
                    for(int j = 0; j < 4; ++j) {
                        if (r + dr[j] == stoppers[i].first && c + dc[j] == stoppers[i].second) {
                            int new_mask = mask | (1 << i);
                            if (cost + 1 < dist[r][c][new_mask]) {
                                dist[r][c][new_mask] = cost + 1;
                                pq.push({cost + 1, r, c, new_mask});
                                parent[r][c][new_mask] = {r, c, mask, 'A', d_char[j]};
                            }
                        }
                    }
                }
            }
        }
        
        if (best_mask == -1) { 
            int tr = target_pos.first, tc = target_pos.second;
            int cr = current_pos.first, cc = current_pos.second;
            while(cr < tr) { solution.push_back({'M','D'}); cr++; }
            while(cr > tr) { solution.push_back({'M','U'}); cr--; }
            while(cc < tc) { solution.push_back({'M','R'}); cc++; }
            while(cc > tc) { solution.push_back({'M','L'}); cc--; }
            current_pos = target_pos;
            continue;
        }

        vector<pair<char, char>> path;
        int cur_r = target_pos.first, cur_c = target_pos.second, cur_mask = best_mask;
        while (cur_r != current_pos.first || cur_c != current_pos.second || cur_mask != 0) {
            ParentInfo p = parent[cur_r][cur_c][cur_mask];
            path.push_back({p.action, p.dir});
            cur_r = p.r;
            cur_c = p.c;
            cur_mask = p.mask;
        }
        reverse(path.begin(), path.end());
        
        for(const auto& p : path) {
            solution.push_back(p);
        }

        pair<int,int> pos_after_path = target_pos;
        vector<bool> stoppers_cleaned(4, false);

        for (int cleanup_iter = 0; cleanup_iter < 4; ++cleanup_iter) {
            bool cleaned_one = false;
            for (int i = 0; i < 4; ++i) {
                if (((best_mask >> i) & 1) && is_stopper_valid[i] && !stoppers_cleaned[i]) {
                    pair<int, int> s_pos = stoppers[i];
                    
                    queue<pair<int,int>> q_cl;
                    q_cl.push(pos_after_path);
                    map<pair<int,int>, pair<pair<int,int>, char>> parent_cl;
                    parent_cl[pos_after_path] = {{-1,-1}, ' '};
                    pair<int, int> neighbor_pos = {-1,-1};

                    auto is_blocked_cl = [&](int r, int c){
                        if (r < 0 || r >= N || c < 0 || c >= N) return true;
                        if (blocks[r][c]) return true;
                        for(int bit=0; bit<4; ++bit) {
                            if(((best_mask >> bit) & 1) && is_stopper_valid[bit] && !stoppers_cleaned[bit] && stoppers[bit].first == r && stoppers[bit].second == c)
                                return true;
                        }
                        return false;
                    };

                    while(!q_cl.empty()) {
                        auto [r, c] = q_cl.front();
                        q_cl.pop();

                        bool found_neighbor = false;
                        for(int j=0; j<4; ++j) {
                           if(r + dr[j] == s_pos.first && c + dc[j] == s_pos.second) {
                               neighbor_pos = {r,c};
                               found_neighbor = true;
                               break;
                           }
                        }
                        if(found_neighbor) break;

                        for(int j=0; j<4; ++j) {
                            int nr = r + dr[j];
                            int nc = c + dc[j];
                            if(!is_blocked_cl(nr, nc) && parent_cl.find({nr,nc}) == parent_cl.end()){
                                parent_cl[{nr,nc}] = {{r,c}, d_char[j]};
                                q_cl.push({nr,nc});
                            }
                        }
                    }

                    if(neighbor_pos.first != -1){
                        vector<pair<char,char>> cleanup_path;
                        pair<int,int> curr = neighbor_pos;
                        while(parent_cl[curr].first.first != -1) {
                            auto p_info = parent_cl[curr];
                            cleanup_path.push_back({'M', p_info.second});
                            curr = p_info.first;
                        }
                        reverse(cleanup_path.begin(), cleanup_path.end());
                        for(auto p_ : cleanup_path) solution.push_back(p_);
                        
                        char remove_dir = ' ';
                        for(int j=0; j<4; ++j) {
                            if(neighbor_pos.first + dr[j] == s_pos.first && neighbor_pos.second + dc[j] == s_pos.second) {
                                remove_dir = d_char[j];
                                break;
                            }
                        }
                        solution.push_back({'A', remove_dir});
                        pos_after_path = neighbor_pos;
                        stoppers_cleaned[i] = true;
                        cleaned_one = true;
                        break; 
                    }
                }
            }
            if(!cleaned_one) break;
        }
        current_pos = target_pos;
    }

    for (const auto& p : solution) {
        cout << p.first << " " << p.second << "\n";
    }

    return 0;
}