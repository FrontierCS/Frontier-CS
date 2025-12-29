#include <iostream>
#include <vector>
#include <string>
#include <numeric>
#include <algorithm>
#include <map>
#include <tuple>
#include <queue>

using namespace std;

const int N_fixed = 20;
int N, M;
vector<string> S;
vector<int> s_to_unique;
vector<string> unique_s;

struct Placement {
    int r, c, dir; // dir 0: hor, 1: ver
    bool operator<(const Placement& other) const {
        if (r != other.r) return r < other.r;
        if (c != other.c) return c < other.c;
        return dir < other.dir;
    }
};

struct Pos {
    int r, c;
};

// rel_placements[unique_s_idx1][unique_s_idx2][dir1][dir2]
vector<pair<short, short>> rel_placements[800][800][2][2];
vector<int> rel_scores[800][800][2][2];

Pos get_pos(int r, int c, int dir, int p) {
    if (dir == 0) return {(r), (c + p) % N};
    return {(r + p) % N, (c)};
}

void precompute() {
    map<string, int> unique_map;
    for (int i = 0; i < M; ++i) {
        if (unique_map.find(S[i]) == unique_map.end()) {
            unique_map[S[i]] = unique_s.size();
            unique_s.push_back(S[i]);
        }
        s_to_unique.push_back(unique_map[S[i]]);
    }

    int num_unique = unique_s.size();
    for (int i = 0; i < num_unique; ++i) {
        for (int j = 0; j < num_unique; ++j) {
            const string& s1 = unique_s[i];
            const string& s2 = unique_s[j];
            int L1 = s1.length();
            int L2 = s2.length();

            // H, H
            for (int dr = 0; dr < 1; ++dr) {
                for (int dc = 0; dc < N; ++dc) {
                    int score = 0;
                    bool possible = true;
                    for (int p1 = 0; p1 < L1; ++p1) {
                        for (int p2 = 0; p2 < L2; ++p2) {
                            if ((0 + p1) % N == (0 + p2) % N) { // Same row is implicit
                                // Should be (c1+p1)%N == (c2+p2)%N => (c1+p1)%N == (c1+dc+p2)%N
                                // p1 % N == (dc+p2)%N
                                if ((p1 - p2 + N) % N == dc) {
                                    if (s1[p1] != s2[p2]) {
                                        possible = false;
                                        break;
                                    }
                                    score++;
                                }
                            }
                        }
                        if (!possible) break;
                    }
                    if (possible) {
                        rel_placements[i][j][0][0].push_back({(short)dr, (short)dc});
                        rel_scores[i][j][0][0].push_back(score);
                    }
                }
            }

            // V, V
            for (int dc = 0; dc < 1; ++dc) {
                for (int dr = 0; dr < N; ++dr) {
                    int score = 0;
                    bool possible = true;
                    for (int p1 = 0; p1 < L1; ++p1) {
                        for (int p2 = 0; p2 < L2; ++p2) {
                            if ((p1 - p2 + N) % N == dr) {
                                if (s1[p1] != s2[p2]) {
                                    possible = false;
                                    break;
                                }
                                score++;
                            }
                        }
                        if (!possible) break;
                    }
                    if (possible) {
                        rel_placements[i][j][1][1].push_back({(short)dr, (short)dc});
                        rel_scores[i][j][1][1].push_back(score);
                    }
                }
            }

            // H, V
            for (int p1 = 0; p1 < L1; ++p1) {
                for (int p2 = 0; p2 < L2; ++p2) {
                    if (s1[p1] == s2[p2]) {
                        int dr = (0 - p2 + N) % N;
                        int dc = (p1 - 0 + N) % N;
                        
                        bool exists = false;
                        for(const auto& pl : rel_placements[i][j][0][1]){
                            if(pl.first == dr && pl.second == dc){
                                exists = true;
                                break;
                            }
                        }
                        if (exists) continue;

                        int score = 0;
                        bool possible = true;
                        for (int pp1 = 0; pp1 < L1; ++pp1) {
                            for (int pp2 = 0; pp2 < L2; ++pp2) {
                                Pos pos1 = get_pos(0, 0, 0, pp1);
                                Pos pos2 = get_pos(dr, dc, 1, pp2);
                                if (pos1.r == pos2.r && pos1.c == pos2.c) {
                                    if (s1[pp1] != s2[pp2]) {
                                        possible = false;
                                        break;
                                    }
                                    score++;
                                }
                            }
                            if (!possible) break;
                        }

                        if (possible) {
                            rel_placements[i][j][0][1].push_back({(short)dr, (short)dc});
                            rel_scores[i][j][0][1].push_back(score);
                        }
                    }
                }
            }
             // V, H
            for (int p1 = 0; p1 < L1; ++p1) {
                for (int p2 = 0; p2 < L2; ++p2) {
                    if (s1[p1] == s2[p2]) {
                        int dr = (p1 - 0 + N) % N;
                        int dc = (0 - p2 + N) % N;

                        bool exists = false;
                        for(const auto& pl : rel_placements[i][j][1][0]){
                            if(pl.first == dr && pl.second == dc){
                                exists = true;
                                break;
                            }
                        }
                        if (exists) continue;


                        int score = 0;
                        bool possible = true;
                        for (int pp1 = 0; pp1 < L1; ++pp1) {
                            for (int pp2 = 0; pp2 < L2; ++pp2) {
                                Pos pos1 = get_pos(0, 0, 1, pp1);
                                Pos pos2 = get_pos(dr, dc, 0, pp2);
                                if (pos1.r == pos2.r && pos1.c == pos2.c) {
                                    if (s1[pp1] != s2[pp2]) {
                                        possible = false;
                                        break;
                                    }
                                    score++;
                                }
                            }
                            if (!possible) break;
                        }

                        if (possible) {
                            rel_placements[i][j][1][0].push_back({(short)dr, (short)dc});
                            rel_scores[i][j][1][0].push_back(score);
                        }
                    }
                }
            }
        }
    }
}


vector<string> solve() {
    int best_start_s_idx = 0;
    for (int i = 1; i < M; ++i) {
        if (S[i].length() > S[best_start_s_idx].length()) {
            best_start_s_idx = i;
        }
    }

    vector<Placement> best_placements_vec;
    int max_dots = -1;

    for (int start_dir = 0; start_dir < 2; ++start_dir) {
        vector<Placement> placements(M);
        vector<bool> placed(M, false);
        
        placements[best_start_s_idx] = {0, 0, start_dir};
        placed[best_start_s_idx] = true;
        int num_placed = 1;

        vector<vector<vector<int>>> score_grid(M, vector<vector<int>>(2, vector<int>(N, 0)));
        vector<vector<vector<int>>> consistency_grid(M, vector<vector<int>>(2, vector<int>(N, 0)));
        
        priority_queue<pair<int, int>> pq;

        // Initialize with the first placed string
        for (int j = 0; j < M; ++j) {
            if (placed[j]) continue;
            int u_j = s_to_unique[j];
            int u_start = s_to_unique[best_start_s_idx];
            
            for (int j_dir = 0; j_dir < 2; ++j_dir) {
                const auto& rels = rel_placements[u_j][u_start][j_dir][start_dir];
                const auto& scores = rel_scores[u_j][u_start][j_dir][start_dir];
                for (size_t i = 0; i < rels.size(); ++i) {
                    int r = rels[i].first;
                    int c = rels[i].second;
                    score_grid[j][j_dir][r][c] += scores[i];
                    consistency_grid[j][j_dir][r][c]++;
                }
            }

            int best_score = -1;
            for (int dir = 0; dir < 2; ++dir) {
                for (int r = 0; r < N; ++r) {
                    for (int c = 0; c < N; ++c) {
                        if (consistency_grid[j][dir][r][c] == num_placed) {
                            if (score_grid[j][dir][r][c] > best_score) {
                                best_score = score_grid[j][dir][r][c];
                            }
                        }
                    }
                }
            }
            if (best_score != -1) {
                pq.push({best_score, j});
            }
        }
        
        while (num_placed < M) {
            int s_to_place_idx = -1;
            while(!pq.empty()){
                s_to_place_idx = pq.top().second;
                pq.pop();
                if(!placed[s_to_place_idx]) break;
                s_to_place_idx = -1;
            }

            if (s_to_place_idx == -1) break;

            int best_score = -1;
            Placement best_placement;

            for (int dir = 0; dir < 2; ++dir) {
                for (int r = 0; r < N; ++r) {
                    for (int c = 0; c < N; ++c) {
                        if (consistency_grid[s_to_place_idx][dir][r][c] == num_placed) {
                            if (score_grid[s_to_place_idx][dir][r][c] > best_score) {
                                best_score = score_grid[s_to_place_idx][dir][r][c];
                                best_placement = {r, c, dir};
                            }
                        }
                    }
                }
            }

            placements[s_to_place_idx] = best_placement;
            placed[s_to_place_idx] = true;
            num_placed++;
            if (num_placed == M) break;
            
            int u_placed = s_to_unique[s_to_place_idx];
            int p_dir = best_placement.dir;
            int p_r = best_placement.r;
            int p_c = best_placement.c;

            for (int j = 0; j < M; ++j) {
                if (placed[j]) continue;
                int u_j = s_to_unique[j];

                for (int j_dir = 0; j_dir < 2; ++j_dir) {
                    const auto& rels = rel_placements[u_j][u_placed][j_dir][p_dir];
                    const auto& scores = rel_scores[u_j][u_placed][j_dir][p_dir];
                    for (size_t i = 0; i < rels.size(); ++i) {
                        int r = (p_r + rels[i].first) % N;
                        int c = (p_c + rels[i].second) % N;
                        score_grid[j][j_dir][r][c] += scores[i];
                        consistency_grid[j][j_dir][r][c]++;
                    }
                }
                
                int current_best_score = -1;
                 for (int dir = 0; dir < 2; ++dir) {
                    for (int r = 0; r < N; ++r) {
                        for (int c = 0; c < N; ++c) {
                            if (consistency_grid[j][dir][r][c] == num_placed) {
                                if (score_grid[j][dir][r][c] > current_best_score) {
                                    current_best_score = score_grid[j][dir][r][c];
                                }
                            }
                        }
                    }
                }

                if (current_best_score != -1) {
                    pq.push({current_best_score, j});
                }
            }
        }
        
        vector<string> grid(N, string(N, '.'));
        int dots = N * N;
        if(num_placed == M){
            vector<vector<bool>> is_set(N, vector<bool>(N, false));
            for(int i=0; i<M; ++i){
                const auto& p = placements[i];
                for(size_t k=0; k<S[i].length(); ++k){
                    Pos pos = get_pos(p.r, p.c, p.dir, k);
                    if(!is_set[pos.r][pos.c]){
                       is_set[pos.r][pos.c] = true;
                       dots--;
                    }
                    grid[pos.r][pos.c] = S[i][k];
                }
            }
        }

        if (dots > max_dots) {
            max_dots = dots;
            best_placements_vec = placements;
        }
    }

    vector<string> final_grid(N, string(N, '.'));
    for (int i = 0; i < M; ++i) {
        if(best_placements_vec.empty()) break;
        const auto& p = best_placements_vec[i];
        for (size_t k = 0; k < S[i].length(); ++k) {
            Pos pos = get_pos(p.r, p.c, p.dir, k);
            final_grid[pos.r][pos.c] = S[i][k];
        }
    }
    return final_grid;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    cin >> N >> M;
    S.resize(M);
    for (int i = 0; i < M; ++i) {
        cin >> S[i];
    }
    
    precompute();
    vector<string> result = solve();

    for (int i = 0; i < N; ++i) {
        cout << result[i] << endl;
    }

    return 0;
}