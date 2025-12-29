#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <cmath>
#include <algorithm>
#include <iomanip>
#include <tuple>

using namespace std;

const int GRID_SIZE = 30;
const int NUM_QUERIES = 1000;
const int PHASE1_END = 200;
const int REDETECT_INTERVAL = 100;
const double SPLIT_VAR_RATIO_THR = 0.7;
const double BETA = 0.3;
const double INIT_W = 5000.0;
const double INIT_N = 10.0;

// Estimated weights
double h_w[GRID_SIZE][GRID_SIZE - 1];
double v_w[GRID_SIZE - 1][GRID_SIZE];

// Statistics for individual edges
double h_S[GRID_SIZE][GRID_SIZE - 1];
double v_S[GRID_SIZE - 1][GRID_SIZE];
double h_N[GRID_SIZE][GRID_SIZE - 1];
double v_N[GRID_SIZE - 1][GRID_SIZE];

// Grouped estimates for Phase 2
double h_w_grouped[GRID_SIZE][GRID_SIZE - 1];
double v_w_grouped[GRID_SIZE - 1][GRID_SIZE];
int h_split[GRID_SIZE];
int v_split[GRID_SIZE];

// Dijkstra's
double dist[GRID_SIZE][GRID_SIZE];
pair<int, int> parent[GRID_SIZE][GRID_SIZE];

void init() {
    for (int i = 0; i < GRID_SIZE; ++i) {
        for (int j = 0; j < GRID_SIZE - 1; ++j) {
            h_w[i][j] = INIT_W;
            h_S[i][j] = INIT_W * INIT_N;
            h_N[i][j] = INIT_N;
        }
    }
    for (int i = 0; i < GRID_SIZE - 1; ++i) {
        for (int j = 0; j < GRID_SIZE; ++j) {
            v_w[i][j] = INIT_W;
            v_S[i][j] = INIT_W * INIT_N;
            v_N[i][j] = INIT_N;
        }
    }
}

string find_path(int si, int sj, int ti, int tj, double h_costs[GRID_SIZE][GRID_SIZE - 1], double v_costs[GRID_SIZE - 1][GRID_SIZE]) {
    for (int i = 0; i < GRID_SIZE; ++i) {
        for (int j = 0; j < GRID_SIZE; ++j) {
            dist[i][j] = 1e18;
        }
    }

    dist[si][sj] = 0;
    priority_queue<tuple<double, int, int>, vector<tuple<double, int, int>>, greater<tuple<double, int, int>>> pq;
    pq.emplace(0, si, sj);

    while (!pq.empty()) {
        auto [d, r, c] = pq.top();
        pq.pop();

        if (d > dist[r][c]) {
            continue;
        }
        if (r == ti && c == tj) break;

        // Moves: U, D, L, R
        if (r > 0) { // U
            double cost = v_costs[r - 1][c];
            if (dist[r][c] + cost < dist[r - 1][c]) {
                dist[r - 1][c] = dist[r][c] + cost;
                parent[r - 1][c] = {r, c};
                pq.emplace(dist[r - 1][c], r - 1, c);
            }
        }
        if (r < GRID_SIZE - 1) { // D
            double cost = v_costs[r][c];
            if (dist[r][c] + cost < dist[r + 1][c]) {
                dist[r + 1][c] = dist[r][c] + cost;
                parent[r + 1][c] = {r, c};
                pq.emplace(dist[r + 1][c], r + 1, c);
            }
        }
        if (c > 0) { // L
            double cost = h_costs[r][c - 1];
            if (dist[r][c] + cost < dist[r][c - 1]) {
                dist[r][c - 1] = dist[r][c] + cost;
                parent[r][c - 1] = {r, c};
                pq.emplace(dist[r][c - 1], r, c - 1);
            }
        }
        if (c < GRID_SIZE - 1) { // R
            double cost = h_costs[r][c];
            if (dist[r][c] + cost < dist[r][c + 1]) {
                dist[r][c + 1] = dist[r][c] + cost;
                parent[r][c + 1] = {r, c};
                pq.emplace(dist[r][c + 1], r, c + 1);
            }
        }
    }

    string path_str = "";
    pair<int, int> curr = {ti, tj};
    while (curr.first != si || curr.second != sj) {
        pair<int, int> p = parent[curr.first][curr.second];
        if (p.first == curr.first + 1) path_str += 'U';
        else if (p.first == curr.first - 1) path_str += 'D';
        else if (p.second == curr.second + 1) path_str += 'L';
        else path_str += 'R';
        curr = p;
    }
    reverse(path_str.begin(), path_str.end());
    return path_str;
}

void update_and_smooth(const string& path, int si, int sj, int measured_cost) {
    double estimated_cost = 0;
    int r = si, c = sj;
    for (char move : path) {
        if (move == 'U') {
            estimated_cost += v_w[r - 1][c]; r--;
        } else if (move == 'D') {
            estimated_cost += v_w[r][c]; r++;
        } else if (move == 'L') {
            estimated_cost += h_w[r][c - 1]; c--;
        } else {
            estimated_cost += h_w[r][c]; c++;
        }
    }

    double ratio = (estimated_cost > 0) ? measured_cost / estimated_cost : 1.0;
    r = si, c = sj;
    for (char move : path) {
        if (move == 'U') {
            v_S[r - 1][c] += v_w[r-1][c] * ratio; v_N[r - 1][c] += 1; v_w[r - 1][c] = v_S[r-1][c] / v_N[r-1][c]; r--;
        } else if (move == 'D') {
            v_S[r][c] += v_w[r][c] * ratio; v_N[r][c] += 1; v_w[r][c] = v_S[r][c] / v_N[r][c]; r++;
        } else if (move == 'L') {
            h_S[r][c - 1] += h_w[r][c-1] * ratio; h_N[r][c - 1] += 1; h_w[r][c - 1] = h_S[r][c-1] / h_N[r][c-1]; c--;
        } else {
            h_S[r][c] += h_w[r][c] * ratio; h_N[r][c] += 1; h_w[r][c] = h_S[r][c] / h_N[r][c]; c++;
        }
    }
    
    double next_h_w[GRID_SIZE][GRID_SIZE - 1];
    double next_v_w[GRID_SIZE - 1][GRID_SIZE];

    for (int i = 0; i < GRID_SIZE; ++i) {
        for (int j = 0; j < GRID_SIZE - 1; ++j) {
            double neighbors_avg = 0; int neighbors_count = 0;
            if (j > 0) { neighbors_avg += h_w[i][j - 1]; neighbors_count++; }
            if (j < GRID_SIZE - 2) { neighbors_avg += h_w[i][j + 1]; neighbors_count++; }
            if (neighbors_count > 0) {
                neighbors_avg /= neighbors_count;
                next_h_w[i][j] = (1.0 - BETA) * h_w[i][j] + BETA * neighbors_avg;
            } else {
                next_h_w[i][j] = h_w[i][j];
            }
        }
    }
    for (int i = 0; i < GRID_SIZE - 1; ++i) {
        for (int j = 0; j < GRID_SIZE; ++j) {
            double neighbors_avg = 0; int neighbors_count = 0;
            if (i > 0) { neighbors_avg += v_w[i - 1][j]; neighbors_count++; }
            if (i < GRID_SIZE - 2) { neighbors_avg += v_w[i + 1][j]; neighbors_count++; }
            if (neighbors_count > 0) {
                neighbors_avg /= neighbors_count;
                next_v_w[i][j] = (1.0 - BETA) * v_w[i][j] + BETA * neighbors_avg;
            } else {
                next_v_w[i][j] = v_w[i][j];
            }
        }
    }
    for (int i = 0; i < GRID_SIZE; ++i) for (int j = 0; j < GRID_SIZE - 1; ++j) h_w[i][j] = next_h_w[i][j];
    for (int i = 0; i < GRID_SIZE - 1; ++i) for (int j = 0; j < GRID_SIZE; ++j) v_w[i][j] = next_v_w[i][j];
}

void detect_splits_and_update_grouped_costs() {
    for (int i = 0; i < GRID_SIZE; ++i) {
        vector<long double> s1(GRID_SIZE, 0), s2(GRID_SIZE, 0);
        s1[0] = h_w[i][0]; s2[0] = h_w[i][0] * h_w[i][0];
        for (int j = 1; j < GRID_SIZE - 1; ++j) {
            s1[j] = s1[j-1] + h_w[i][j]; s2[j] = s2[j-1] + h_w[i][j] * h_w[i][j];
        }
        long double min_var = 1e18; int best_split = -1;
        for (int j = 1; j < GRID_SIZE - 1; ++j) {
            long double l_s1 = s1[j - 1], l_s2 = s2[j - 1];
            long double l_var = l_s2 - l_s1 * l_s1 / j;
            long double r_s1 = s1[GRID_SIZE - 2] - s1[j - 1], r_s2 = s2[GRID_SIZE - 2] - s2[j - 1];
            int r_cnt = GRID_SIZE - 1 - j;
            long double r_var = r_s2 - r_s1 * r_s1 / r_cnt;
            if (l_var + r_var < min_var) { min_var = l_var + r_var; best_split = j; }
        }
        long double tot_s1 = s1[GRID_SIZE - 2], tot_s2 = s2[GRID_SIZE - 2];
        long double tot_var = tot_s2 - tot_s1 * tot_s1 / (GRID_SIZE - 1);
        h_split[i] = (min_var < tot_var * SPLIT_VAR_RATIO_THR) ? best_split : -1;
    }
    
    for (int j = 0; j < GRID_SIZE; ++j) {
        vector<long double> s1(GRID_SIZE, 0), s2(GRID_SIZE, 0);
        s1[0] = v_w[0][j]; s2[0] = v_w[0][j] * v_w[0][j];
        for (int i = 1; i < GRID_SIZE - 1; ++i) {
            s1[i] = s1[i-1] + v_w[i][j]; s2[i] = s2[i-1] + v_w[i][j] * v_w[i][j];
        }
        long double min_var = 1e18; int best_split = -1;
        for (int i = 1; i < GRID_SIZE - 1; ++i) {
            long double l_s1 = s1[i-1], l_s2 = s2[i-1];
            long double l_var = l_s2 - l_s1 * l_s1 / i;
            long double r_s1 = s1[GRID_SIZE-2] - s1[i-1], r_s2 = s2[GRID_SIZE-2] - s2[i-1];
            int r_cnt = GRID_SIZE - 1 - i;
            long double r_var = r_s2 - r_s1 * r_s1 / r_cnt;
            if (l_var + r_var < min_var) { min_var = l_var + r_var; best_split = i; }
        }
        long double tot_s1 = s1[GRID_SIZE-2], tot_s2 = s2[GRID_SIZE-2];
        long double tot_var = tot_s2 - tot_s1 * tot_s1 / (GRID_SIZE - 1);
        v_split[j] = (min_var < tot_var * SPLIT_VAR_RATIO_THR) ? best_split : -1;
    }
    
    for (int i = 0; i < GRID_SIZE; ++i) {
        if (h_split[i] == -1) {
            double sum = 0; for(int j=0; j<GRID_SIZE-1; ++j) sum += h_w[i][j];
            double avg = sum / (GRID_SIZE-1); for(int j=0; j<GRID_SIZE-1; ++j) h_w_grouped[i][j] = avg;
        } else {
            double s_l=0, s_r=0; int split = h_split[i];
            for(int j=0; j<split; ++j) s_l+=h_w[i][j]; for(int j=split; j<GRID_SIZE-1; ++j) s_r+=h_w[i][j];
            double avg_l = s_l / split, avg_r = s_r / (GRID_SIZE-1-split);
            for(int j=0; j<split; ++j) h_w_grouped[i][j] = avg_l; for(int j=split; j<GRID_SIZE-1; ++j) h_w_grouped[i][j] = avg_r;
        }
    }
    for (int j = 0; j < GRID_SIZE; ++j) {
        if (v_split[j] == -1) {
            double sum = 0; for(int i=0; i<GRID_SIZE-1; ++i) sum+=v_w[i][j];
            double avg = sum/(GRID_SIZE-1); for(int i=0; i<GRID_SIZE-1; ++i) v_w_grouped[i][j]=avg;
        } else {
            double s_l=0, s_r=0; int split=v_split[j];
            for(int i=0; i<split; ++i) s_l+=v_w[i][j]; for(int i=split; i<GRID_SIZE-1; ++i) s_r+=v_w[i][j];
            double avg_l=s_l/split, avg_r=s_r/(GRID_SIZE-1-split);
            for(int i=0; i<split; ++i) v_w_grouped[i][j]=avg_l; for(int i=split; i<GRID_SIZE-1; ++i) v_w_grouped[i][j]=avg_r;
        }
    }
}

void update_in_phase2(const string& path, int si, int sj, int measured_cost) {
    double estimated_cost = 0;
    int r = si, c = sj;
    for (char move : path) {
        if (move == 'U') { estimated_cost += v_w_grouped[r-1][c]; r--; }
        else if (move == 'D') { estimated_cost += v_w_grouped[r][c]; r++; }
        else if (move == 'L') { estimated_cost += h_w_grouped[r][c-1]; c--; }
        else { estimated_cost += h_w_grouped[r][c]; c++; }
    }

    double ratio = (estimated_cost > 0) ? measured_cost / estimated_cost : 1.0;
    r = si, c = sj;
    for (char move : path) {
        if (move == 'U') {
            v_S[r - 1][c] += v_w_grouped[r-1][c] * ratio; v_N[r - 1][c] += 1; v_w[r-1][c] = v_S[r-1][c]/v_N[r-1][c]; r--;
        } else if (move == 'D') {
            v_S[r][c] += v_w_grouped[r][c] * ratio; v_N[r][c] += 1; v_w[r][c] = v_S[r][c]/v_N[r][c]; r++;
        } else if (move == 'L') {
            h_S[r][c - 1] += h_w_grouped[r][c-1] * ratio; h_N[r][c - 1] += 1; h_w[r][c-1] = h_S[r][c-1]/h_N[r][c-1]; c--;
        } else {
            h_S[r][c] += h_w_grouped[r][c] * ratio; h_N[r][c] += 1; h_w[r][c] = h_S[r][c]/h_N[r][c]; c++;
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    init();

    for (int k = 0; k < NUM_QUERIES; ++k) {
        int si, sj, ti, tj;
        cin >> si >> sj >> ti >> tj;

        string path;
        if (k < PHASE1_END) {
            path = find_path(si, sj, ti, tj, h_w, v_w);
        } else {
            if (k == PHASE1_END || (k > PHASE1_END && k % REDETECT_INTERVAL == 0)) {
                detect_splits_and_update_grouped_costs();
            }
            path = find_path(si, sj, ti, tj, h_w_grouped, v_w_grouped);
        }

        cout << path << endl;

        int measured_cost;
        cin >> measured_cost;

        if (k < PHASE1_END) {
            update_and_smooth(path, si, sj, measured_cost);
        } else {
            update_in_phase2(path, si, sj, measured_cost);
        }
    }

    return 0;
}