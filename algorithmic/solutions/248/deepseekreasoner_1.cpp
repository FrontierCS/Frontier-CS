#include <bits/stdc++.h>
using namespace std;

double A, B;
int M;
vector<int> n_city;
vector<int> x_city;
vector<vector<int>> y_city;
vector<vector<double*>> cost_mat; // cost_mat[i][j] is pointer to array of size n_city[i]*n_city[j] for i!=j

double compute_cost(int i, int p, int j, int q) {
    double dx = abs(x_city[i] - x_city[j]);
    if (dx < 1e-9) dx = 1e-9;
    double dy = y_city[j][q] - y_city[i][p];
    double dist = sqrt(dx*dx + (y_city[i][p] - y_city[j][q])*(y_city[i][p] - y_city[j][q]));
    double slope = (dy > 0) ? dy / dx : 0.0;
    return A * dist + B * slope;
}

void precompute_costs() {
    cost_mat.assign(M, vector<double*>(M, nullptr));
    for (int i = 0; i < M; i++) {
        for (int j = 0; j < M; j++) {
            if (i == j) continue;
            int ni = n_city[i];
            int nj = n_city[j];
            double* arr = new double[ni * nj];
            cost_mat[i][j] = arr;
            for (int p = 0; p < ni; p++) {
                for (int q = 0; q < nj; q++) {
                    arr[p * nj + q] = compute_cost(i, p, j, q);
                }
            }
        }
    }
}

pair<double, vector<int>> compute_best_for_perm(const vector<int>& perm) {
    int len = perm.size();
    double best_total = 1e100;
    vector<int> best_points(len);
    int start_city = perm[0];
    int n0 = n_city[start_city];
    for (int p0 = 0; p0 < n0; p0++) {
        vector<vector<double>> dp(len);
        vector<vector<int>> prev(len);
        for (int t = 0; t < len; t++) {
            int city = perm[t];
            dp[t].assign(n_city[city], 1e100);
            prev[t].assign(n_city[city], -1);
        }
        dp[0][p0] = 0.0;
        for (int t = 1; t < len; t++) {
            int cur_city = perm[t];
            int prev_city = perm[t-1];
            int n_cur = n_city[cur_city];
            int n_prev = n_city[prev_city];
            double* cost_arr = cost_mat[prev_city][cur_city];
            for (int q = 0; q < n_cur; q++) {
                double best = 1e100;
                int best_p = -1;
                for (int p = 0; p < n_prev; p++) {
                    double val = dp[t-1][p] + cost_arr[p * n_cur + q];
                    if (val < best) {
                        best = val;
                        best_p = p;
                    }
                }
                dp[t][q] = best;
                prev[t][q] = best_p;
            }
        }
        int last_city = perm[len-1];
        int first_city = start_city;
        double* cost_back = cost_mat[last_city][first_city];
        int n_last = n_city[last_city];
        int n_first = n_city[first_city];
        double total = 1e100;
        int best_q_last = -1;
        for (int q = 0; q < n_last; q++) {
            double val = dp[len-1][q] + cost_back[q * n_first + p0];
            if (val < total) {
                total = val;
                best_q_last = q;
            }
        }
        if (total < best_total) {
            best_total = total;
            vector<int> points(len);
            points[0] = p0;
            points[len-1] = best_q_last;
            for (int t = len-1; t >= 1; t--) {
                int q = points[t];
                int p = prev[t][q];
                points[t-1] = p;
            }
            best_points = points;
        }
    }
    return {best_total, best_points};
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);
    srand(time(0));
    double base;
    cin >> base;
    cin >> M;
    n_city.resize(M);
    x_city.resize(M);
    y_city.resize(M);
    for (int i = 0; i < M; i++) {
        cin >> n_city[i] >> x_city[i];
        y_city[i].resize(n_city[i]);
        for (int j = 0; j < n_city[i]; j++) {
            cin >> y_city[i][j];
        }
    }
    int D_input, S_input;
    cin >> D_input >> S_input;
    double k = 0.6;
    A = (1.0 - k) / D_input;
    B = k / S_input;

    precompute_costs();

    vector<vector<double>> d_min(M, vector<double>(M, 1e100));
    for (int i = 0; i < M; i++) {
        for (int j = 0; j < M; j++) {
            if (i == j) continue;
            int ni = n_city[i];
            int nj = n_city[j];
            double* arr = cost_mat[i][j];
            double min_val = 1e100;
            for (int p = 0; p < ni; p++) {
                for (int q = 0; q < nj; q++) {
                    min_val = min(min_val, arr[p * nj + q]);
                }
            }
            d_min[i][j] = min_val;
        }
    }

    // Greedy initial permutation with random start
    vector<int> best_perm;
    double best_cost = 1e100;
    vector<int> best_points;
    const int GREEDY_TRIALS = 10;
    for (int trial = 0; trial < GREEDY_TRIALS; trial++) {
        vector<int> perm(M);
        vector<bool> visited(M, false);
        int start = rand() % M;
        perm[0] = start;
        visited[start] = true;
        for (int i = 1; i < M; i++) {
            int last = perm[i-1];
            double best = 1e100;
            int best_j = -1;
            for (int j = 0; j < M; j++) {
                if (!visited[j] && d_min[last][j] < best) {
                    best = d_min[last][j];
                    best_j = j;
                }
            }
            perm[i] = best_j;
            visited[best_j] = true;
        }
        auto [cost, points] = compute_best_for_perm(perm);
        if (cost < best_cost) {
            best_cost = cost;
            best_perm = perm;
            best_points = points;
        }
    }

    vector<int> perm = best_perm;
    double current_cost = best_cost;
    vector<int> current_points = best_points;

    // Simulated Annealing
    int max_iter = 10000;
    double T0 = 0.0;
    const int temp_trials = 100;
    double avg_increase = 0.0;
    int count_increase = 0;
    for (int t = 0; t < temp_trials; t++) {
        vector<int> trial_perm = perm;
        int a = rand() % M;
        int b = rand() % M;
        while (a == b) b = rand() % M;
        swap(trial_perm[a], trial_perm[b]);
        auto [new_cost, _] = compute_best_for_perm(trial_perm);
        if (new_cost > current_cost) {
            avg_increase += (new_cost - current_cost);
            count_increase++;
        }
    }
    if (count_increase > 0) {
        avg_increase /= count_increase;
        T0 = avg_increase / log(2);
    } else {
        T0 = current_cost * 0.1;
    }
    double T = T0;
    double cooling_rate = 0.9995;

    for (int iter = 0; iter < max_iter; iter++) {
        vector<int> new_perm = perm;
        if (rand() % 2 == 0) {
            int a = rand() % M;
            int b = rand() % M;
            while (a == b) b = rand() % M;
            swap(new_perm[a], new_perm[b]);
        } else {
            int a = rand() % M;
            int b = rand() % M;
            if (a > b) swap(a, b);
            reverse(new_perm.begin() + a, new_perm.begin() + b + 1);
        }
        auto [new_cost, new_points] = compute_best_for_perm(new_perm);
        if (new_cost < current_cost || (double)rand() / RAND_MAX < exp((current_cost - new_cost) / T)) {
            current_cost = new_cost;
            perm = new_perm;
            current_points = new_points;
        }
        T *= cooling_rate;
    }

    // Output
    for (int i = 0; i < M; i++) {
        cout << "(" << perm[i]+1 << "," << current_points[i]+1 << ")";
        if (i < M-1) cout << "@";
    }
    cout << endl;

    // Clean up
    for (int i = 0; i < M; i++) {
        for (int j = 0; j < M; j++) {
            if (cost_mat[i][j] != nullptr) {
                delete[] cost_mat[i][j];
            }
        }
    }

    return 0;
}