#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <cmath>
#include <algorithm>
#include <iomanip>

const int N = 30;
const int Q = 1000;
const double INITIAL_WEIGHT = 5000.0;
const int INITIAL_COUNT = 5;
const double MIN_WEIGHT = 1000.0;
const double MAX_WEIGHT = 9000.0;
const double SMOOTHING_BETA = 0.1;

// h_est[i][j]: edge between (i, j) and (i, j+1)
double h_est[N][N - 1];
long long h_cnt[N][N - 1];

// v_est[i][j]: edge between (i, j) and (i+1, j)
double v_est[N - 1][N];
long long v_cnt[N - 1][N];

struct State {
    double cost;
    int r, c;

    bool operator>(const State& other) const {
        return cost > other.cost;
    }
};

double dist[N][N];
int parent_r[N][N];
int parent_c[N][N];

void dijkstra(int si, int sj) {
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            dist[i][j] = 1e18;
            parent_r[i][j] = -1;
            parent_c[i][j] = -1;
        }
    }

    dist[si][sj] = 0;
    std::priority_queue<State, std::vector<State>, std::greater<State>> pq;
    pq.push({0.0, si, sj});

    while (!pq.empty()) {
        State current = pq.top();
        pq.pop();

        double cost = current.cost;
        int r = current.r;
        int c = current.c;

        if (cost > dist[r][c]) {
            continue;
        }

        // Up
        if (r > 0) {
            double edge_w = v_est[r - 1][c];
            if (dist[r - 1][c] > dist[r][c] + edge_w) {
                dist[r - 1][c] = dist[r][c] + edge_w;
                parent_r[r - 1][c] = r;
                parent_c[r - 1][c] = c;
                pq.push({dist[r - 1][c], r - 1, c});
            }
        }
        // Down
        if (r < N - 1) {
            double edge_w = v_est[r][c];
            if (dist[r + 1][c] > dist[r][c] + edge_w) {
                dist[r + 1][c] = dist[r][c] + edge_w;
                parent_r[r + 1][c] = r;
                parent_c[r + 1][c] = c;
                pq.push({dist[r + 1][c], r + 1, c});
            }
        }
        // Left
        if (c > 0) {
            double edge_w = h_est[r][c - 1];
            if (dist[r][c - 1] > dist[r][c] + edge_w) {
                dist[r][c - 1] = dist[r][c] + edge_w;
                parent_r[r][c - 1] = r;
                parent_c[r][c - 1] = c;
                pq.push({dist[r][c - 1], r, c - 1});
            }
        }
        // Right
        if (c < N - 1) {
            double edge_w = h_est[r][c];
            if (dist[r][c + 1] > dist[r][c] + edge_w) {
                dist[r][c + 1] = dist[r][c] + edge_w;
                parent_r[r][c + 1] = r;
                parent_c[r][c + 1] = c;
                pq.push({dist[r][c + 1], r, c + 1});
            }
        }
    }
}

void initialize() {
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N - 1; ++j) {
            h_est[i][j] = INITIAL_WEIGHT;
            h_cnt[i][j] = INITIAL_COUNT;
        }
    }
    for (int i = 0; i < N - 1; ++i) {
        for (int j = 0; j < N; ++j) {
            v_est[i][j] = INITIAL_WEIGHT;
            v_cnt[i][j] = INITIAL_COUNT;
        }
    }
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    initialize();

    for (int k = 0; k < Q; ++k) {
        int si, sj, ti, tj;
        std::cin >> si >> sj >> ti >> tj;

        dijkstra(si, sj);

        std::string path = "";
        int cur_r = ti, cur_c = tj;
        while (cur_r != si || cur_c != sj) {
            int pr = parent_r[cur_r][cur_c];
            int pc = parent_c[cur_r][cur_c];
            if (pr == cur_r + 1) path += 'U';
            else if (pr == cur_r - 1) path += 'D';
            else if (pc == cur_c + 1) path += 'L';
            else path += 'R';
            cur_r = pr;
            cur_c = pc;
        }
        std::reverse(path.begin(), path.end());

        std::cout << path << std::endl;

        long long actual_path_len;
        std::cin >> actual_path_len;

        double estimated_path_len = 0;
        int r = si, c = sj;
        for (char move : path) {
            if (move == 'U') {
                estimated_path_len += v_est[r - 1][c]; r--;
            } else if (move == 'D') {
                estimated_path_len += v_est[r][c]; r++;
            } else if (move == 'L') {
                estimated_path_len += h_est[r][c - 1]; c--;
            } else { // 'R'
                estimated_path_len += h_est[r][c]; c++;
            }
        }

        r = si; c = sj;
        for (char move : path) {
            double* w_ptr;
            long long* cnt_ptr;
            if (move == 'U') {
                w_ptr = &v_est[r-1][c]; cnt_ptr = &v_cnt[r-1][c]; r--;
            } else if (move == 'D') {
                w_ptr = &v_est[r][c]; cnt_ptr = &v_cnt[r][c]; r++;
            } else if (move == 'L') {
                w_ptr = &h_est[r][c-1]; cnt_ptr = &h_cnt[r][c-1]; c--;
            } else { // 'R'
                w_ptr = &h_est[r][c]; cnt_ptr = &h_cnt[r][c]; c++;
            }
            
            double alpha = 1.0 / (*cnt_ptr);
            double new_w = *w_ptr * (1.0 - alpha + alpha * actual_path_len / estimated_path_len);
            *w_ptr = std::max(MIN_WEIGHT, std::min(MAX_WEIGHT, new_w));
            (*cnt_ptr)++;
        }

        double h_temp[N][N-1];
        for (int i=0; i<N; ++i) for (int j=0; j<N-1; ++j) h_temp[i][j] = h_est[i][j];
        
        for (int i = 0; i < N; ++i) {
            for (int j = 0; j < N - 1; ++j) {
                double avg = 0;
                int num_neighbors = 0;
                if (j > 0) { avg += h_temp[i][j - 1]; num_neighbors++; }
                if (j < N - 2) { avg += h_temp[i][j + 1]; num_neighbors++; }
                if (num_neighbors > 0) {
                    avg /= num_neighbors;
                    double new_h = (1.0 - SMOOTHING_BETA) * h_temp[i][j] + SMOOTHING_BETA * avg;
                    h_est[i][j] = std::max(MIN_WEIGHT, std::min(MAX_WEIGHT, new_h));
                }
            }
        }

        double v_temp[N-1][N];
        for (int i=0; i<N-1; ++i) for (int j=0; j<N; ++j) v_temp[i][j] = v_est[i][j];

        for (int j = 0; j < N; ++j) {
            for (int i = 0; i < N - 1; ++i) {
                double avg = 0;
                int num_neighbors = 0;
                if (i > 0) { avg += v_temp[i - 1][j]; num_neighbors++; }
                if (i < N - 2) { avg += v_temp[i + 1][j]; num_neighbors++; }
                if (num_neighbors > 0) {
                    avg /= num_neighbors;
                    double new_v = (1.0 - SMOOTHING_BETA) * v_temp[i][j] + SMOOTHING_BETA * avg;
                    v_est[i][j] = std::max(MIN_WEIGHT, std::min(MAX_WEIGHT, new_v));
                }
            }
        }
    }

    return 0;
}