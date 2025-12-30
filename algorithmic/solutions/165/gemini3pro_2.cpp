#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <cmath>
#include <ctime>
#include <random>
#include <climits>
#include <chrono>

using namespace std;

const int N = 15;
const int M_MAX = 200;
int start_r, start_c;
char grid[N][N];
vector<string> targets;
int M;

vector<pair<int, int>> char_positions[26];
int overlaps[M_MAX][M_MAX];
int dist_mat[M_MAX][M_MAX];

void compute_overlaps() {
    for (int i = 0; i < M; ++i) {
        for (int j = 0; j < M; ++j) {
            if (i == j) {
                overlaps[i][j] = 0; 
                dist_mat[i][j] = 5; 
                continue;
            }
            int max_ov = 0;
            for (int k = 1; k < 5; ++k) {
                if (targets[i].substr(5 - k) == targets[j].substr(0, k)) {
                    max_ov = k;
                }
            }
            overlaps[i][j] = max_ov;
            dist_mat[i][j] = 5 - max_ov;
        }
    }
}

int evaluate_permutation(const vector<int>& p) {
    if (p.empty()) return 0;
    int len = 5;
    for (size_t i = 0; i < p.size() - 1; ++i) {
        len += dist_mat[p[i]][p[i+1]];
    }
    return len;
}

string construct_string(const vector<int>& p) {
    if (p.empty()) return "";
    string s = targets[p[0]];
    for (size_t i = 0; i < p.size() - 1; ++i) {
        int u = p[i];
        int v = p[i+1];
        int ov = overlaps[u][v];
        s += targets[v].substr(ov);
    }
    return s;
}

vector<int> solve_tsp() {
    vector<int> best_initial_p;
    int best_initial_len = 1e9;

    for (int start_node = 0; start_node < M; ++start_node) {
        vector<int> p;
        p.reserve(M);
        vector<bool> used(M, false);
        
        p.push_back(start_node);
        used[start_node] = true;
        
        int current = start_node;
        int len = 5;
        
        for (int i = 1; i < M; ++i) {
            int best_next = -1;
            int min_cost = 6;
            
            for (int j = 0; j < M; ++j) {
                if (!used[j]) {
                    if (dist_mat[current][j] < min_cost) {
                        min_cost = dist_mat[current][j];
                        best_next = j;
                    }
                }
            }
            
            p.push_back(best_next);
            used[best_next] = true;
            len += min_cost;
            current = best_next;
        }
        
        if (len < best_initial_len) {
            best_initial_len = len;
            best_initial_p = p;
        }
    }

    vector<int> p = best_initial_p;
    int current_len = best_initial_len;
    
    vector<int> best_p = p;
    int best_len = current_len;

    double t_start = 2.0;
    double t_end = 0.005;
    auto start_time = chrono::high_resolution_clock::now();
    double time_limit = 1.85;

    mt19937 rng(1337);

    while(true) {
        auto now = chrono::high_resolution_clock::now();
        chrono::duration<double> elapsed = now - start_time;
        if(elapsed.count() > time_limit) break;

        double progress = elapsed.count() / time_limit;
        double temp = t_start * pow(t_end / t_start, progress);

        int move_type = rng() % 2;
        
        if (move_type == 0) {
            int i = rng() % M;
            int j = rng() % M;
            if (i == j) continue;
            if (i > j) swap(i, j);
            
            int delta = 0;
            if (j == i + 1) {
                int u = p[i];
                int v = p[j];
                int a = (i > 0) ? p[i-1] : -1;
                int b = (j < M-1) ? p[j+1] : -1;
                
                if (a != -1) delta -= dist_mat[a][u];
                delta -= dist_mat[u][v];
                if (b != -1) delta -= dist_mat[v][b];
                
                if (a != -1) delta += dist_mat[a][v];
                delta += dist_mat[v][u];
                if (b != -1) delta += dist_mat[u][b];
            } else {
                int u = p[i];
                int v = p[j];
                int a = (i > 0) ? p[i-1] : -1;
                int b = p[i+1];
                int c = p[j-1]; 
                int d = (j < M-1) ? p[j+1] : -1;
                
                if (a != -1) delta -= dist_mat[a][u];
                delta -= dist_mat[u][b];
                delta -= dist_mat[c][v];
                if (d != -1) delta -= dist_mat[v][d];
                
                if (a != -1) delta += dist_mat[a][v];
                delta += dist_mat[v][b];
                delta += dist_mat[c][u];
                if (d != -1) delta += dist_mat[u][d];
            }
            
            if (delta < 0 || bernoulli_distribution(exp(-delta / temp))(rng)) {
                swap(p[i], p[j]);
                current_len += delta;
                if (current_len < best_len) {
                    best_len = current_len;
                    best_p = p;
                }
            }
        } else {
            int src = rng() % M;
            int dst = rng() % (M + 1);
            if (dst == src || dst == src + 1) continue;
            
            int val = p[src];
            p.erase(p.begin() + src);
            int actual_dst = (dst > src) ? dst - 1 : dst;
            p.insert(p.begin() + actual_dst, val);
            
            int new_len = evaluate_permutation(p);
            int delta = new_len - current_len;
            
            if (delta < 0 || bernoulli_distribution(exp(-delta / temp))(rng)) {
                current_len = new_len;
                if (current_len < best_len) {
                    best_len = current_len;
                    best_p = p;
                }
            } else {
                p.erase(p.begin() + actual_dst);
                p.insert(p.begin() + src, val);
            }
        }
    }
    return best_p;
}

struct Point {
    int r, c;
};

int dist(Point a, Point b) {
    return abs(a.r - b.r) + abs(a.c - b.c);
}

void solve_dp(const string& S) {
    int L = S.length();
    if (L == 0) return;
    
    vector<vector<int>> costs(L);
    vector<vector<short>> parents(L);
    
    int char_idx_0 = S[0] - 'A';
    const auto& pos_0 = char_positions[char_idx_0];
    int num_pos_0 = pos_0.size();
    
    costs[0].resize(num_pos_0);
    parents[0].resize(num_pos_0, -1);
    
    Point start_pt = {start_r, start_c};
    
    for(int j=0; j<num_pos_0; ++j) {
        costs[0][j] = dist(start_pt, pos_0[j]) + 1;
    }
    
    for(int i=1; i<L; ++i) {
        int c_curr = S[i] - 'A';
        int c_prev = S[i-1] - 'A';
        const auto& pos_curr = char_positions[c_curr];
        const auto& pos_prev = char_positions[c_prev];
        int num_curr = pos_curr.size();
        int num_prev = pos_prev.size();
        
        costs[i].resize(num_curr, 1e9);
        parents[i].resize(num_curr, -1);
        
        for(int cur=0; cur<num_curr; ++cur) {
            Point p_cur = pos_curr[cur];
            int best_val = 1e9;
            short best_p = -1;
            
            for(int prev=0; prev<num_prev; ++prev) {
                int d = costs[i-1][prev] + dist(pos_prev[prev], p_cur) + 1;
                if(d < best_val) {
                    best_val = d;
                    best_p = (short)prev;
                }
            }
            costs[i][cur] = best_val;
            parents[i][cur] = best_p;
        }
    }
    
    int best_cost = 1e9;
    int best_end_idx = -1;
    int num_last = costs[L-1].size();
    for(int j=0; j<num_last; ++j) {
        if(costs[L-1][j] < best_cost) {
            best_cost = costs[L-1][j];
            best_end_idx = j;
        }
    }
    
    vector<Point> path;
    path.reserve(L);
    int cur_idx = best_end_idx;
    for(int i=L-1; i>=0; --i) {
        path.push_back(char_positions[S[i] - 'A'][cur_idx]);
        cur_idx = parents[i][cur_idx];
    }
    reverse(path.begin(), path.end());
    
    for(const auto& pt : path) {
        cout << pt.r << " " << pt.c << "\n";
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    
    int n_temp;
    if (!(cin >> n_temp >> M)) return 0;
    
    cin >> start_r >> start_c;
    
    for(int i=0; i<N; ++i) {
        string row;
        cin >> row;
        for(int j=0; j<N; ++j) {
            grid[i][j] = row[j];
            char_positions[row[j] - 'A'].push_back({i, j});
        }
    }
    
    targets.resize(M);
    for(int i=0; i<M; ++i) {
        cin >> targets[i];
    }
    
    compute_overlaps();
    
    vector<int> best_perm = solve_tsp();
    string S = construct_string(best_perm);
    
    solve_dp(S);
    
    return 0;
}