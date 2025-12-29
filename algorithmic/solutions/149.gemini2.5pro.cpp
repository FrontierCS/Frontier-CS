#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <cmath>
#include <numeric>
#include <algorithm>
#include <iomanip>
#include <tuple>

using namespace std;

const int N = 30;
const int K = 1000;
const int K0 = 400;

// Phase 1: individual edge weights and counts
double h_w[N][N - 1];
double v_w[N - 1][N];
long long h_cnt[N][N - 1];
long long v_cnt[N - 1][N];

// Phase 2: structural model parameters
int M_type = 1;
double H_w[N][2];
double V_w[N][2];
int x_split[N];
int y_split[N];

// Dijkstra variables
double dist[N][N];
int prev_r[N][N];
int prev_c[N][N];
int dr[] = {-1, 1, 0, 0};
int dc[] = {0, 0, -1, 1};

struct State {
    double d;
    int r, c;

    bool operator>(const State& other) const {
        return d > other.d;
    }
};

double get_edge_weight(int r, int c, int dir_idx, int k) {
    if (k < K0) {
        if (dir_idx == 0) return v_w[r - 1][c]; // U
        if (dir_idx == 1) return v_w[r][c];     // D
        if (dir_idx == 2) return h_w[r][c - 1]; // L
        if (dir_idx == 3) return h_w[r][c];     // R
    } else {
        if (dir_idx == 0) { // U from r to r-1
            if (M_type == 1) return V_w[c][0];
            return (r - 1 < y_split[c]) ? V_w[c][0] : V_w[c][1];
        }
        if (dir_idx == 1) { // D from r to r+1
            if (M_type == 1) return V_w[c][0];
            return (r < y_split[c]) ? V_w[c][0] : V_w[c][1];
        }
        if (dir_idx == 2) { // L from c to c-1
            if (M_type == 1) return H_w[r][0];
            return (c - 1 < x_split[r]) ? H_w[r][0] : H_w[r][1];
        }
        if (dir_idx == 3) { // R from c to c+1
            if (M_type == 1) return H_w[r][0];
            return (c < x_split[r]) ? H_w[r][0] : H_w[r][1];
        }
    }
    return 5000.0;
}

void fit_model() {
    double total_e1_h = 0, total_e2_h = 0;
    for (int i = 0; i < N; ++i) {
        double sum_w = 0, sum_w_h = 0;
        for (int j = 0; j < N - 1; ++j) {
            sum_w += h_cnt[i][j];
            sum_w_h += h_w[i][j] * h_cnt[i][j];
        }
        double mean_h = (sum_w > 0) ? sum_w_h / sum_w : 5000.0;
        double e1 = 0;
        for (int j = 0; j < N - 1; ++j) {
            e1 += h_cnt[i][j] * pow(h_w[i][j] - mean_h, 2);
        }
        total_e1_h += e1;
        
        double min_e2 = 1e18;
        for (int p = 1; p < N - 1; ++p) {
            double s_w1=0, s_wh1=0, s_w2=0, s_wh2=0;
            for(int j=0; j<p; ++j) { s_w1 += h_cnt[i][j]; s_wh1 += h_w[i][j]*h_cnt[i][j]; }
            for(int j=p; j<N-1; ++j) { s_w2 += h_cnt[i][j]; s_wh2 += h_w[i][j]*h_cnt[i][j]; }
            if (s_w1 == 0 || s_w2 == 0) continue;
            double m1 = s_wh1/s_w1, m2 = s_wh2/s_w2;
            double e2 = 0;
            for(int j=0; j<p; ++j) e2 += h_cnt[i][j] * pow(h_w[i][j]-m1,2);
            for(int j=p; j<N-1; ++j) e2 += h_cnt[i][j] * pow(h_w[i][j]-m2,2);
            if (e2 < min_e2) {
                min_e2 = e2;
                x_split[i] = p;
                H_w[i][0] = m1;
                H_w[i][1] = m2;
            }
        }
        if (min_e2 > 1e17) min_e2 = e1;
        total_e2_h += min_e2;
    }

    double total_e1_v = 0, total_e2_v = 0;
    for (int j = 0; j < N; ++j) {
        double sum_w = 0, sum_w_v = 0;
        for (int i = 0; i < N - 1; ++i) {
            sum_w += v_cnt[i][j];
            sum_w_v += v_w[i][j] * v_cnt[i][j];
        }
        double mean_v = (sum_w > 0) ? sum_w_v / sum_w : 5000.0;
        double e1 = 0;
        for (int i = 0; i < N - 1; ++i) {
            e1 += v_cnt[i][j] * pow(v_w[i][j] - mean_v, 2);
        }
        total_e1_v += e1;
        
        double min_e2 = 1e18;
        for (int p = 1; p < N - 1; ++p) {
            double s_w1=0, s_wv1=0, s_w2=0, s_wv2=0;
            for(int i=0; i<p; ++i) { s_w1 += v_cnt[i][j]; s_wv1 += v_w[i][j]*v_cnt[i][j]; }
            for(int i=p; i<N-1; ++i) { s_w2 += v_cnt[i][j]; s_wv2 += v_w[i][j]*v_cnt[i][j]; }
            if (s_w1 == 0 || s_w2 == 0) continue;
            double m1 = s_wv1/s_w1, m2 = s_wv2/s_w2;
            double e2 = 0;
            for(int i=0; i<p; ++i) e2 += v_cnt[i][j] * pow(v_w[i][j]-m1,2);
            for(int i=p; i<N-1; ++i) e2 += v_cnt[i][j] * pow(v_w[i][j]-m2,2);
            if (e2 < min_e2) {
                min_e2 = e2;
                y_split[j] = p;
                V_w[j][0] = m1;
                V_w[j][1] = m2;
            }
        }
        if(min_e2 > 1e17) min_e2 = e1;
        total_e2_v += min_e2;
    }

    if ((total_e2_h + total_e2_v) * 1.25 < total_e1_h + total_e1_v) {
        M_type = 2;
    } else {
        M_type = 1;
        for(int i=0; i<N; ++i) {
            double sum_w = 0, sum_w_h = 0;
            for(int j=0; j<N-1; ++j) { sum_w += h_cnt[i][j]; sum_w_h += h_w[i][j]*h_cnt[i][j]; }
            H_w[i][0] = (sum_w > 0) ? sum_w_h/sum_w : 5000.0;
        }
        for(int j=0; j<N; ++j) {
            double sum_w = 0, sum_w_v = 0;
            for(int i=0; i<N-1; ++i) { sum_w += v_cnt[i][j]; sum_w_v += v_w[i][j]*v_cnt[i][j]; }
            V_w[j][0] = (sum_w > 0) ? sum_w_v/sum_w : 5000.0;
        }
    }
}


int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N - 1; ++j) {
            h_w[i][j] = 5000.0;
            h_cnt[i][j] = 1;
        }
    }
    for (int i = 0; i < N - 1; ++i) {
        for (int j = 0; j < N; ++j) {
            v_w[i][j] = 5000.0;
            v_cnt[i][j] = 1;
        }
    }

    for (int k = 0; k < K; ++k) {
        if (k == K0) {
            fit_model();
        }

        int si, sj, ti, tj;
        cin >> si >> sj >> ti >> tj;

        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N; ++j) {
                dist[i][j] = 1e18;
            }
        }

        priority_queue<State, vector<State>, greater<State>> pq;
        dist[si][sj] = 0;
        pq.push({0, si, sj});

        while (!pq.empty()) {
            State current = pq.top();
            pq.pop();

            if (current.d > dist[current.r][current.c]) {
                continue;
            }
            if (current.r == ti && current.c == tj) {
                break;
            }

            for (int i = 0; i < 4; ++i) {
                int nr = current.r + dr[i];
                int nc = current.c + dc[i];

                if (nr >= 0 && nr < N && nc >= 0 && nc < N) {
                    double weight = get_edge_weight(current.r, current.c, i, k);
                    if (dist[current.r][current.c] + weight < dist[nr][nc]) {
                        dist[nr][nc] = dist[current.r][current.c] + weight;
                        prev_r[nr][nc] = current.r;
                        prev_c[nr][nc] = current.c;
                        pq.push({dist[nr][nc], nr, nc});
                    }
                }
            }
        }

        string path_str = "";
        int cur_r = ti, cur_c = tj;
        double path_len_est = 0;
        vector<tuple<int,int,int,int>> path_edges;
        
        while (cur_r != si || cur_c != sj) {
            int pr = prev_r[cur_r][cur_c];
            int pc = prev_c[cur_r][cur_c];
            path_edges.emplace_back(pr, pc, cur_r, cur_c);
            if (pr == cur_r + 1) path_str += 'U';
            else if (pr == cur_r - 1) path_str += 'D';
            else if (pc == cur_c + 1) path_str += 'L';
            else if (pc == cur_c - 1) path_str += 'R';
            cur_r = pr;
            cur_c = pc;
        }
        reverse(path_str.begin(), path_str.end());
        cout << path_str << endl;

        long long actual_path_len_noisy;
        cin >> actual_path_len_noisy;

        for(const auto& edge : path_edges) {
            int r1, c1, r2, c2;
            tie(r1, c1, r2, c2) = edge;
            int dir = -1;
            if (r2 == r1 - 1) dir = 0; // U
            else if (r2 == r1 + 1) dir = 1; // D
            else if (c2 == c1 - 1) dir = 2; // L
            else if (c2 == c1 + 1) dir = 3; // R
            path_len_est += get_edge_weight(r1, c1, dir, k);
        }

        if (k < K0) {
            double alpha = 0.2;
            double diff = actual_path_len_noisy - path_len_est;
            if (path_str.length() == 0) continue;
            double correction = alpha * diff / path_str.length();
            
            for(const auto& edge : path_edges) {
                int r1, c1, r2, c2;
                tie(r1, c1, r2, c2) = edge;
                if (r1 == r2) { // horizontal
                    int c = min(c1, c2);
                    h_w[r1][c] += correction;
                    h_w[r1][c] = max(1000.0, min(9000.0, h_w[r1][c]));
                    h_cnt[r1][c]++;
                } else { // vertical
                    int r = min(r1, r2);
                    v_w[r][c1] += correction;
                    v_w[r][c1] = max(1000.0, min(9000.0, v_w[r][c1]));
                    v_cnt[r][c1]++;
                }
            }
        } else {
            double eta = 0.2;
            double diff = actual_path_len_noisy - path_len_est;
            vector<int> nh_counts(N*2,0), nv_counts(N*2,0);

            for(const auto& edge : path_edges) {
                int r1, c1, r2, c2;
                tie(r1, c1, r2, c2) = edge;
                if(r1 == r2) { // horizontal
                    int c = min(c1,c2);
                    if (M_type == 1) nh_counts[r1*2]++;
                    else {
                        if (c < x_split[r1]) nh_counts[r1*2]++;
                        else nh_counts[r1*2+1]++;
                    }
                } else { // vertical
                    int r = min(r1,r2);
                    if (M_type == 1) nv_counts[c1*2]++;
                    else {
                        if (r < y_split[c1]) nv_counts[c1*2]++;
                        else nv_counts[c1*2+1]++;
                    }
                }
            }
            
            double norm_factor = 0;
            for(int count : nh_counts) norm_factor += count*count;
            for(int count : nv_counts) norm_factor += count*count;
            if (norm_factor == 0) norm_factor = 1;

            for (int i=0; i<N; ++i) {
                for(int p=0; p<M_type; ++p) {
                    if (nh_counts[i*2+p] > 0) {
                        H_w[i][p] += eta * diff * nh_counts[i*2+p] / norm_factor;
                        H_w[i][p] = max(1000.0, min(9000.0, H_w[i][p]));
                    }
                }
            }
            for (int j=0; j<N; ++j) {
                for(int p=0; p<M_type; ++p) {
                    if (nv_counts[j*2+p] > 0) {
                        V_w[j][p] += eta * diff * nv_counts[j*2+p] / norm_factor;
                        V_w[j][p] = max(1000.0, min(9000.0, V_w[j][p]));
                    }
                }
            }
        }
    }

    return 0;
}