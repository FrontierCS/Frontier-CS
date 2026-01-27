#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <random>
#include <chrono>
#include <iomanip>
#include <limits>

using namespace std;

const double INF = 1e18;
const double EPS = 1e-9;

// Precomputed cost matrices: cost[i][j] is a flat vector of size n[i]*n[j]
// cost[i][j][p*nj+q] = cost from point p in city i to point q in city j
vector<vector<vector<double>>> cost;

// City data
vector<int> x;                // x coordinate of each city
vector<vector<int>> y;        // list of y coordinates for each city
vector<int> n;                // number of points per city
int M;                        // number of cities
double w1, w2;                // weights for distance and slope

// Precompute cost matrices
void precompute_costs() {
    cost.assign(M, vector<vector<double>>(M));
    for (int i = 0; i < M; ++i) {
        for (int j = 0; j < M; ++j) {
            if (i == j) continue;
            double dx = abs(x[i] - x[j]);
            if (dx == 0) dx = EPS;   // avoid division by zero
            int ni = n[i], nj = n[j];
            cost[i][j].resize(ni * nj);
            for (int p = 0; p < ni; ++p) {
                for (int q = 0; q < nj; ++q) {
                    double dy = y[j][q] - y[i][p];
                    double dist = sqrt(dx*dx + (y[i][p] - y[j][q])*(y[i][p] - y[j][q]));
                    double slope = (dy > 0) ? dy / dx : 0.0;
                    cost[i][j][p*nj + q] = w1 * dist + w2 * slope;
                }
            }
        }
    }
}

// Evaluate a permutation: compute minimal cost and the chosen points
double evaluate(const vector<int>& order, vector<int>& chosen_points) {
    int L = M;
    // dp[i][q]: minimal cost to reach point q in city order[i]
    vector<vector<double>> dp(L, vector<double>());
    vector<vector<int>> prev(L, vector<int>());
    for (int i = 0; i < L; ++i) {
        int c = order[i];
        dp[i].assign(n[c], INF);
        prev[i].assign(n[c], -1);
    }

    double best_total = INF;
    vector<int> best_points(L, 0);

    // Try each possible starting point in the first city
    int first_city = order[0];
    int n_first = n[first_city];
    for (int start = 0; start < n_first; ++start) {
        // Initialize dp for the first city
        dp[0][start] = 0.0;
        // Forward DP
        for (int i = 1; i < L; ++i) {
            int cur_city = order[i];
            int prev_city = order[i-1];
            int n_cur = n[cur_city];
            int n_prev = n[prev_city];
            const vector<double>& cost_mat = cost[prev_city][cur_city];
            for (int q = 0; q < n_cur; ++q) {
                double best = INF;
                int best_p = -1;
                for (int p = 0; p < n_prev; ++p) {
                    double val = dp[i-1][p] + cost_mat[p * n_cur + q];
                    if (val < best) {
                        best = val;
                        best_p = p;
                    }
                }
                dp[i][q] = best;
                prev[i][q] = best_p;
            }
        }
        // Closing edge back to the first city
        int last_city = order[L-1];
        int n_last = n[last_city];
        const vector<double>& closing_cost = cost[last_city][first_city];
        double best_close = INF;
        int best_last = -1;
        for (int q = 0; q < n_last; ++q) {
            double val = dp[L-1][q] + closing_cost[q * n_first + start];
            if (val < best_close) {
                best_close = val;
                best_last = q;
            }
        }
        if (best_close < best_total) {
            best_total = best_close;
            // Backtrack to get points
            best_points[L-1] = best_last;
            for (int i = L-1; i > 0; --i) {
                best_points[i-1] = prev[i][best_points[i]];
            }
            // Check: best_points[0] should be start
        }
        // Reset dp for next start
        for (int i = 0; i < L; ++i) {
            fill(dp[i].begin(), dp[i].end(), INF);
        }
    }

    chosen_points = best_points;
    return best_total;
}

// Generate a random permutation
vector<int> random_permutation(int size, mt19937& rng) {
    vector<int> perm(size);
    iota(perm.begin(), perm.end(), 0);
    shuffle(perm.begin(), perm.end(), rng);
    return perm;
}

// 2-opt move: reverse segment between i+1 and j (inclusive)
vector<int> two_opt(const vector<int>& order, int i, int j) {
    vector<int> new_order = order;
    reverse(new_order.begin() + i + 1, new_order.begin() + j + 1);
    return new_order;
}

// Swap two cities at positions i and j
vector<int> swap_cities(const vector<int>& order, int i, int j) {
    vector<int> new_order = order;
    swap(new_order[i], new_order[j]);
    return new_order;
}

// Move city from position i to position pos (insert before pos)
vector<int> move_city(const vector<int>& order, int i, int pos) {
    vector<int> new_order;
    for (int k = 0; k < (int)order.size(); ++k) {
        if (k == i) continue;
        if (k == pos) new_order.push_back(order[i]);
        new_order.push_back(order[k]);
    }
    if (pos == (int)order.size()) new_order.push_back(order[i]);
    return new_order;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    double base;
    cin >> base;

    cin >> M;
    x.resize(M);
    y.resize(M);
    n.resize(M);

    for (int i = 0; i < M; ++i) {
        cin >> n[i] >> x[i];
        y[i].resize(n[i]);
        for (int j = 0; j < n[i]; ++j) {
            cin >> y[i][j];
        }
    }

    int D, S;
    cin >> D >> S;
    w1 = 0.4 / D;   // (1-k)/D with k=0.6
    w2 = 0.6 / S;   // k/S

    precompute_costs();

    // Random number generator
    mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

    // Generate several initial permutations and pick the best
    const int INIT_TRIALS = 20;
    double best_cost = INF;
    vector<int> best_order(M);
    vector<int> best_points(M);
    for (int trial = 0; trial < INIT_TRIALS; ++trial) {
        vector<int> order = random_permutation(M, rng);
        vector<int> points;
        double cur_cost = evaluate(order, points);
        if (cur_cost < best_cost) {
            best_cost = cur_cost;
            best_order = order;
            best_points = points;
        }
    }

    // Simulated Annealing
    double current_cost = best_cost;
    vector<int> current_order = best_order;
    vector<int> current_points = best_points;

    double T0 = current_cost * 0.1;
    double T = T0;
    const int MAX_ITER = 30000;
    const double COOLING_RATE = 0.99995;
    uniform_real_distribution<double> prob(0.0, 1.0);
    uniform_int_distribution<int> move_type_dist(0, 2);
    uniform_int_distribution<int> pos_dist(0, M-1);

    for (int iter = 0; iter < MAX_ITER; ++iter) {
        // Generate a random move
        vector<int> new_order;
        int move_type = move_type_dist(rng);
        if (move_type == 0) { // 2-opt
            int i = pos_dist(rng);
            int j = pos_dist(rng);
            if (i > j) swap(i, j);
            if (j - i <= 1) continue; // no effect
            new_order = two_opt(current_order, i, j);
        } else if (move_type == 1) { // swap two cities
            int i = pos_dist(rng);
            int j = pos_dist(rng);
            if (i == j) continue;
            new_order = swap_cities(current_order, i, j);
        } else { // move city
            int i = pos_dist(rng);
            int pos = pos_dist(rng);
            if (i == pos) continue;
            new_order = move_city(current_order, i, pos);
        }

        vector<int> new_points;
        double new_cost = evaluate(new_order, new_points);
        double delta = new_cost - current_cost;
        if (delta < 0 || prob(rng) < exp(-delta / T)) {
            current_cost = new_cost;
            current_order = new_order;
            current_points = new_points;
            if (current_cost < best_cost) {
                best_cost = current_cost;
                best_order = current_order;
                best_points = current_points;
            }
        }
        T *= COOLING_RATE;
    }

    // Output the best solution found
    for (int i = 0; i < M; ++i) {
        cout << "(" << best_order[i] + 1 << "," << best_points[i] + 1 << ")";
        if (i < M-1) cout << "@";
    }
    cout << endl;

    return 0;
}