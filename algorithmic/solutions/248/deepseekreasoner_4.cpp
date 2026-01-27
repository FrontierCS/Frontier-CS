#include <iostream>
#include <vector>
#include <algorithm>
#include <cmath>
#include <random>
#include <chrono>
#include <iomanip>

using namespace std;

const double k = 0.6;
const double INF = 1e18;
const double EPS = 1e-9;

// Global data
int M; // number of cities
vector<int> n; // number of points per city
vector<int> x; // x-coordinate of each city
vector<vector<int>> y; // y-coordinates of points per city
double D, S; // normalization constants

// Precomputed cost: cost[i][j][p][q] = cost from point p in city i to point q in city j
vector<vector<vector<vector<double>>>> cost;

// Random number generator
mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

// Helper function to compute Euclidean distance
inline double euclidean(double dx, double dy) {
    return sqrt(dx*dx + dy*dy);
}

// Precompute all costs between points of different cities
void precompute_costs() {
    cost.assign(M, vector<vector<vector<double>>>(M));
    for (int i = 0; i < M; ++i) {
        for (int j = 0; j < M; ++j) {
            if (i == j) continue;
            double dx = x[i] - x[j];
            double horizontal = fabs(dx);
            if (horizontal < 1e-9) horizontal = 1e-9; // avoid division by zero
            double dx2 = dx*dx;
            cost[i][j].resize(n[i], vector<double>(n[j]));
            for (int p = 0; p < n[i]; ++p) {
                for (int q = 0; q < n[j]; ++q) {
                    double dy = y[i][p] - y[j][q];
                    double dist = euclidean(dx, dy);
                    double slope = 0.0;
                    if (y[j][q] > y[i][p]) {
                        slope = (y[j][q] - y[i][p]) / horizontal;
                    }
                    double c = (1.0 - k) * dist / D + k * slope / S;
                    cost[i][j][p][q] = c;
                }
            }
        }
    }
}

// Compute total cost of a given order and point assignment
double compute_cost(const vector<int>& order, const vector<int>& points) {
    double total = 0.0;
    int L = order.size();
    for (int idx = 0; idx < L; ++idx) {
        int i = order[idx];
        int j = order[(idx+1)%L];
        total += cost[i][j][points[i]][points[j]];
    }
    return total;
}

// Dynamic programming to find optimal points for a fixed order (cycle)
// Returns {cost, points_assignment} where points_assignment[i] is point index for city i
pair<double, vector<int>> dp_for_order(const vector<int>& order) {
    int L = order.size();
    // DP tables: dp[i][r] = min cost up to city i ending with point r
    vector<vector<double>> dp(L);
    vector<vector<int>> pre(L);
    for (int i = 0; i < L; ++i) {
        int city = order[i];
        dp[i].assign(n[city], INF);
        pre[i].assign(n[city], -1);
    }

    double best_total = INF;
    vector<int> best_points(M, -1);

    int first_city = order[0];
    int n0 = n[first_city];
    // Try each possible point for the first city
    for (int r0 = 0; r0 < n0; ++r0) {
        // Initialize
        for (int i = 0; i < L; ++i) {
            fill(dp[i].begin(), dp[i].end(), INF);
            fill(pre[i].begin(), pre[i].end(), -1);
        }
        dp[0][r0] = 0.0;

        // Forward DP
        for (int i = 1; i < L; ++i) {
            int cur_city = order[i];
            int prev_city = order[i-1];
            for (int r_cur = 0; r_cur < n[cur_city]; ++r_cur) {
                double best = INF;
                int best_prev = -1;
                for (int r_prev = 0; r_prev < n[prev_city]; ++r_prev) {
                    double edge = cost[prev_city][cur_city][r_prev][r_cur];
                    double cand = dp[i-1][r_prev] + edge;
                    if (cand < best) {
                        best = cand;
                        best_prev = r_prev;
                    }
                }
                dp[i][r_cur] = best;
                pre[i][r_cur] = best_prev;
            }
        }

        // Close the cycle
        int last_city = order[L-1];
        double total = INF;
        int best_last = -1;
        for (int r_last = 0; r_last < n[last_city]; ++r_last) {
            double edge = cost[last_city][first_city][r_last][r0];
            double cand = dp[L-1][r_last] + edge;
            if (cand < total) {
                total = cand;
                best_last = r_last;
            }
        }

        if (total < best_total) {
            best_total = total;
            // Backtrack to get point assignments
            vector<int> points(M, -1);
            points[first_city] = r0;
            int cur_point = best_last;
            for (int i = L-1; i >= 1; --i) {
                int city = order[i];
                points[city] = cur_point;
                cur_point = pre[i][cur_point];
            }
            best_points = points;
        }
    }
    return {best_total, best_points};
}

// Generate a random permutation of cities
vector<int> random_order() {
    vector<int> order(M);
    iota(order.begin(), order.end(), 0);
    shuffle(order.begin(), order.end(), rng);
    return order;
}

// Generate initial order sorted by x-coordinate
vector<int> initial_order_by_x() {
    vector<int> order(M);
    iota(order.begin(), order.end(), 0);
    sort(order.begin(), order.end(), [&](int a, int b) {
        return x[a] < x[b];
    });
    return order;
}

// Perturb an order by performing a number of random swaps
void perturb_order(vector<int>& order, int swaps = 10) {
    for (int t = 0; t < swaps; ++t) {
        int a = rng() % M;
        int b = rng() % M;
        while (a == b) b = rng() % M;
        swap(order[a], order[b]);
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    double base;
    cin >> base; // not used in algorithm

    cin >> M;
    n.resize(M);
    x.resize(M);
    y.resize(M);
    for (int i = 0; i < M; ++i) {
        cin >> n[i] >> x[i];
        y[i].resize(n[i]);
        for (int j = 0; j < n[i]; ++j) {
            cin >> y[i][j];
        }
    }
    cin >> D >> S; // normalization constants

    precompute_costs();

    // Time control
    auto start_time = chrono::steady_clock::now();
    const double max_time = 14.0; // seconds

    // Best solution found
    double best_cost = INF;
    vector<int> best_order;
    vector<int> best_points;

    bool first_run = true;
    while (true) {
        auto now = chrono::steady_clock::now();
        chrono::duration<double> elapsed = now - start_time;
        if (elapsed.count() >= max_time) break;

        // Initial order
        vector<int> order;
        if (first_run) {
            order = initial_order_by_x();
            first_run = false;
        } else {
            order = random_order();
        }

        // Initial points via DP
        auto [cur_cost, cur_points] = dp_for_order(order);
        vector<int> cur_order = order;

        // Local search on order
        bool improved = true;
        while (improved) {
            improved = false;

            // Swap moves
            vector<pair<int,int>> swaps;
            for (int i = 0; i < M; ++i) {
                for (int j = i+1; j < M; ++j) {
                    swaps.emplace_back(i, j);
                }
            }
            shuffle(swaps.begin(), swaps.end(), rng);

            for (auto [i,j] : swaps) {
                // Check time
                auto now2 = chrono::steady_clock::now();
                if (chrono::duration<double>(now2 - start_time).count() >= max_time) {
                    // Time's up, break out
                    break;
                }

                // Generate new order by swapping i and j
                vector<int> new_order = cur_order;
                swap(new_order[i], new_order[j]);
                // Compute cost with current points
                double new_cost_with_old_points = compute_cost(new_order, cur_points);
                if (new_cost_with_old_points < cur_cost - EPS) {
                    // Accept swap and re-optimize points
                    auto [new_cost, new_points] = dp_for_order(new_order);
                    if (new_cost < cur_cost - EPS) {
                        cur_order = new_order;
                        cur_points = new_points;
                        cur_cost = new_cost;
                        improved = true;
                        break;
                    }
                }
            }
            if (improved) continue;

            // Insert moves
            vector<pair<int,int>> inserts; // (city_position, new_position)
            for (int pos = 0; pos < M; ++pos) {
                for (int newpos = 0; newpos < M; ++newpos) {
                    if (pos == newpos) continue;
                    inserts.emplace_back(pos, newpos);
                }
            }
            shuffle(inserts.begin(), inserts.end(), rng);

            for (auto [pos, newpos] : inserts) {
                auto now2 = chrono::steady_clock::now();
                if (chrono::duration<double>(now2 - start_time).count() >= max_time) break;

                // Generate new order by moving city at 'pos' to 'newpos'
                vector<int> new_order;
                if (newpos < pos) {
                    // Insert before
                    for (int i = 0; i < newpos; ++i) new_order.push_back(cur_order[i]);
                    new_order.push_back(cur_order[pos]);
                    for (int i = newpos; i < M; ++i) if (i != pos) new_order.push_back(cur_order[i]);
                } else { // newpos > pos
                    for (int i = 0; i <= pos; ++i) if (i != pos) new_order.push_back(cur_order[i]);
                    for (int i = pos+1; i < newpos; ++i) new_order.push_back(cur_order[i]);
                    new_order.push_back(cur_order[pos]);
                    for (int i = newpos; i < M; ++i) new_order.push_back(cur_order[i]);
                }
                double new_cost_with_old_points = compute_cost(new_order, cur_points);
                if (new_cost_with_old_points < cur_cost - EPS) {
                    auto [new_cost, new_points] = dp_for_order(new_order);
                    if (new_cost < cur_cost - EPS) {
                        cur_order = new_order;
                        cur_points = new_points;
                        cur_cost = new_cost;
                        improved = true;
                        break;
                    }
                }
            }

            // If no improvement, break out of local search
        }

        // Update global best
        if (cur_cost < best_cost) {
            best_cost = cur_cost;
            best_order = cur_order;
            best_points = cur_points;
        }

        // Perturb current order for next restart (if time remains)
        perturb_order(cur_order, 5);
        // Re-optimize points for perturbed order
        auto [pert_cost, pert_points] = dp_for_order(cur_order);
        if (pert_cost < best_cost) {
            best_cost = pert_cost;
            best_order = cur_order;
            best_points = pert_points;
        }
    }

    // Output best solution
    for (int i = 0; i < M; ++i) {
        int city = best_order[i];
        int point = best_points[city];
        cout << "(" << city+1 << "," << point+1 << ")";
        if (i < M-1) cout << "@";
    }
    cout << endl;

    return 0;
}