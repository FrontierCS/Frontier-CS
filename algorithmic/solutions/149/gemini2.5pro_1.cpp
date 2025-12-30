#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <cmath>
#include <algorithm>
#include <iomanip>
#include <random>

using namespace std;

const int GRID_SIZE = 30;
const int NUM_QUERIES = 1000;

// Individual edge stats
double h_S[GRID_SIZE][GRID_SIZE - 1];
double v_S[GRID_SIZE - 1][GRID_SIZE];
double h_N[GRID_SIZE][GRID_SIZE - 1];
double v_N[GRID_SIZE - 1][GRID_SIZE];

struct Model {
    int m = 0; // 0: unmodeled, 1: M=1, 2: M=2
    int split_point = 0;
};

// Model state
Model row_model[GRID_SIZE];
Model col_model[GRID_SIZE];

// Group stats
double H_S[GRID_SIZE][2], H_N[GRID_SIZE][2];
double V_S[GRID_SIZE][2], V_N[GRID_SIZE][2];

// Randomness for exploration
mt19937 rng(12345);

struct State {
    int r, c;
    double cost;

    bool operator>(const State& other) const {
        return cost > other.cost;
    }
};

double get_h_cost(int r, int c) {
    if (row_model[r].m == 0) {
        return h_S[r][c] / h_N[r][c];
    } else if (row_model[r].m == 1) {
        return H_S[r][0] / H_N[r][0];
    } else { // m == 2
        int group = (c < row_model[r].split_point) ? 0 : 1;
        return H_S[r][group] / H_N[r][group];
    }
}

double get_v_cost(int r, int c) {
    if (col_model[c].m == 0) {
        return v_S[r][c] / v_N[r][c];
    } else if (col_model[c].m == 1) {
        return V_S[c][0] / V_N[c][0];
    } else { // m == 2
        int group = (r < col_model[c].split_point) ? 0 : 1;
        return V_S[c][group] / V_N[c][group];
    }
}

void build_models() {
    // Build for rows
    for (int i = 0; i < GRID_SIZE; ++i) {
        vector<pair<int, double>> estimates;
        for (int j = 0; j < GRID_SIZE - 1; ++j) {
            if (h_N[i][j] > 3) {
                estimates.push_back({j, h_S[i][j] / h_N[i][j]});
            }
        }
        if (estimates.size() < 6) {
            row_model[i].m = 0;
            continue;
        }

        int n = estimates.size();
        double total_s = 0, total_s2 = 0;
        for (const auto& p : estimates) {
            total_s += p.second;
            total_s2 += p.second * p.second;
        }

        double e1 = total_s2 - total_s * total_s / n;

        double min_e2 = 1e18;
        int best_split_idx = -1;

        double ls = 0, ls2 = 0;
        for (int k = 0; k < n - 1; ++k) {
            ls += estimates[k].second;
            ls2 += estimates[k].second * estimates[k].second;
            int l_count = k + 1;
            int r_count = n - l_count;
            if (l_count < 2 || r_count < 2) continue;

            double rs = total_s - ls;
            double rs2 = total_s2 - ls2;
            double e2 = (ls2 - ls * ls / l_count) + (rs2 - rs * rs / r_count);

            if (e2 < min_e2) {
                min_e2 = e2;
                best_split_idx = k;
            }
        }

        if (best_split_idx != -1 && e1 > 0 && min_e2 > 0) {
            double bic1 = n * log(e1 / n) + 1 * log(n);
            double bic2 = n * log(min_e2 / n) + 2 * log(n);
            if (bic2 < bic1) {
                row_model[i].m = 2;
                row_model[i].split_point = estimates[best_split_idx].first + 1;
            } else {
                row_model[i].m = 1;
            }
        } else {
            row_model[i].m = 1;
        }

        if (row_model[i].m == 1) {
            H_S[i][0] = 0; H_N[i][0] = 0;
            for(int j=0; j<GRID_SIZE-1; ++j) {
                H_S[i][0] += h_S[i][j];
                H_N[i][0] += h_N[i][j];
            }
        } else { // m == 2
            H_S[i][0] = 0; H_N[i][0] = 0;
            H_S[i][1] = 0; H_N[i][1] = 0;
            for(int j=0; j<GRID_SIZE-1; ++j) {
                int group = (j < row_model[i].split_point) ? 0 : 1;
                H_S[i][group] += h_S[i][j];
                H_N[i][group] += h_N[i][j];
            }
        }
    }

    // Build for columns
    for (int j = 0; j < GRID_SIZE; ++j) {
        vector<pair<int, double>> estimates;
        for (int i = 0; i < GRID_SIZE - 1; ++i) {
            if (v_N[i][j] > 3) {
                estimates.push_back({i, v_S[i][j] / v_N[i][j]});
            }
        }
        if (estimates.size() < 6) {
            col_model[j].m = 0;
            continue;
        }
        
        int n = estimates.size();
        double total_s = 0, total_s2 = 0;
        for (const auto& p : estimates) {
            total_s += p.second;
            total_s2 += p.second * p.second;
        }

        double e1 = total_s2 - total_s * total_s / n;

        double min_e2 = 1e18;
        int best_split_idx = -1;

        double ls = 0, ls2 = 0;
        for (int k = 0; k < n - 1; ++k) {
            ls += estimates[k].second;
            ls2 += estimates[k].second * estimates[k].second;
            int l_count = k + 1;
            int r_count = n - l_count;
            if (l_count < 2 || r_count < 2) continue;

            double rs = total_s - ls;
            double rs2 = total_s2 - ls2;
            double e2 = (ls2 - ls * ls / l_count) + (rs2 - rs * rs / r_count);

            if (e2 < min_e2) {
                min_e2 = e2;
                best_split_idx = k;
            }
        }
        
        if (best_split_idx != -1 && e1 > 0 && min_e2 > 0) {
            double bic1 = n * log(e1 / n) + 1 * log(n);
            double bic2 = n * log(min_e2 / n) + 2 * log(n);

            if (bic2 < bic1) {
                col_model[j].m = 2;
                col_model[j].split_point = estimates[best_split_idx].first + 1;
            } else {
                col_model[j].m = 1;
            }
        } else {
            col_model[j].m = 1;
        }

        if (col_model[j].m == 1) {
            V_S[j][0] = 0; V_N[j][0] = 0;
            for(int i=0; i<GRID_SIZE-1; ++i) {
                V_S[j][0] += v_S[i][j];
                V_N[j][0] += v_N[i][j];
            }
        } else { // m == 2
            V_S[j][0] = 0; V_N[j][0] = 0;
            V_S[j][1] = 0; V_N[j][1] = 0;
            for(int i=0; i<GRID_SIZE-1; ++i) {
                int group = (i < col_model[j].split_point) ? 0 : 1;
                V_S[j][group] += v_S[i][j];
                V_N[j][group] += v_N[i][j];
            }
        }
    }
}


int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    for (int i = 0; i < GRID_SIZE; ++i) {
        for (int j = 0; j < GRID_SIZE - 1; ++j) {
            h_S[i][j] = 5000.0;
            h_N[i][j] = 1.0;
        }
    }
    for (int i = 0; i < GRID_SIZE - 1; ++i) {
        for (int j = 0; j < GRID_SIZE; ++j) {
            v_S[i][j] = 5000.0;
            v_N[i][j] = 1.0;
        }
    }

    for (int k = 0; k < NUM_QUERIES; ++k) {
        if (k > 0 && k % 200 == 0) {
            build_models();
        }

        int si, sj, ti, tj;
        cin >> si >> sj >> ti >> tj;

        vector<vector<double>> dist(GRID_SIZE, vector<double>(GRID_SIZE, 1e18));
        vector<vector<pair<int, int>>> parent(GRID_SIZE, vector<pair<int, int>>(GRID_SIZE, {-1, -1}));
        priority_queue<State, vector<State>, greater<State>> pq;

        dist[si][sj] = 0;
        pq.push({si, sj, 0});
        
        double exploration_rate = 0.1 * (1.0 - (double)k / NUM_QUERIES);
        uniform_real_distribution<> distrib(-exploration_rate, exploration_rate);

        while (!pq.empty()) {
            State current = pq.top();
            pq.pop();

            if (current.cost > dist[current.r][current.c]) {
                continue;
            }
            if (current.r == ti && current.c == tj) {
                break;
            }
            
            int r = current.r, c = current.c;
            
            // U
            if (r > 0) {
                double cost = get_v_cost(r - 1, c) * (1.0 + distrib(rng));
                if (dist[r - 1][c] > dist[r][c] + cost) {
                    dist[r - 1][c] = dist[r][c] + cost;
                    parent[r - 1][c] = {r, c};
                    pq.push({r - 1, c, dist[r - 1][c]});
                }
            }
            // D
            if (r < GRID_SIZE - 1) {
                double cost = get_v_cost(r, c) * (1.0 + distrib(rng));
                if (dist[r + 1][c] > dist[r][c] + cost) {
                    dist[r + 1][c] = dist[r][c] + cost;
                    parent[r + 1][c] = {r, c};
                    pq.push({r + 1, c, dist[r + 1][c]});
                }
            }
            // L
            if (c > 0) {
                double cost = get_h_cost(r, c - 1) * (1.0 + distrib(rng));
                if (dist[r][c - 1] > dist[r][c] + cost) {
                    dist[r][c - 1] = dist[r][c] + cost;
                    parent[r][c - 1] = {r, c};
                    pq.push({r, c - 1, dist[r][c - 1]});
                }
            }
            // R
            if (c < GRID_SIZE - 1) {
                double cost = get_h_cost(r, c) * (1.0 + distrib(rng));
                if (dist[r][c + 1] > dist[r][c] + cost) {
                    dist[r][c + 1] = dist[r][c] + cost;
                    parent[r][c + 1] = {r, c};
                    pq.push({r, c + 1, dist[r][c + 1]});
                }
            }
        }

        string path = "";
        int cur_r = ti, cur_c = tj;
        double estimated_b = 0;
        
        while (cur_r != si || cur_c != sj) {
            int pr = parent[cur_r][cur_c].first;
            int pc = parent[cur_r][cur_c].second;
            if (pr == cur_r - 1) { path += 'D'; estimated_b += get_v_cost(pr, pc); }
            else if (pr == cur_r + 1) { path += 'U'; estimated_b += get_v_cost(cur_r, cur_c); }
            else if (pc == cur_c - 1) { path += 'R'; estimated_b += get_h_cost(pr, pc); }
            else { path += 'L'; estimated_b += get_h_cost(cur_r, cur_c); }
            cur_r = pr;
            cur_c = pc;
        }
        reverse(path.begin(), path.end());
        cout << path << endl;

        long long real_b_noisy;
        cin >> real_b_noisy;
        
        double correction_factor = (estimated_b > 0) ? (double)real_b_noisy / estimated_b : 1.0;

        cur_r = si; cur_c = sj;
        for (char move : path) {
            if (move == 'U') {
                double w_est = get_v_cost(cur_r - 1, cur_c);
                v_S[cur_r - 1][cur_c] += w_est * correction_factor;
                v_N[cur_r - 1][cur_c] += 1;
                cur_r--;
            } else if (move == 'D') {
                double w_est = get_v_cost(cur_r, cur_c);
                v_S[cur_r][cur_c] += w_est * correction_factor;
                v_N[cur_r][cur_c] += 1;
                cur_r++;
            } else if (move == 'L') {
                double w_est = get_h_cost(cur_r, cur_c - 1);
                h_S[cur_r][cur_c - 1] += w_est * correction_factor;
                h_N[cur_r][cur_c - 1] += 1;
                cur_c--;
            } else if (move == 'R') {
                double w_est = get_h_cost(cur_r, cur_c);
                h_S[cur_r][cur_c] += w_est * correction_factor;
                h_N[cur_r][cur_c] += 1;
                cur_c++;
            }
        }
    }

    return 0;
}