#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <set>
#include <random>
#include <cassert>

using namespace std;

const double INF = 1e100;
const double EPS = 1e-9;

int M; // number of cities
vector<int> n; // number of landing points per city
vector<int> city_x; // x-coordinate of each city
vector<vector<int>> city_y; // y-coordinates of landing points for each city
double dist_coeff, slope_coeff; // coefficients for distance and slope in cost

// cost[i][j][p][q] = cost from point p of city i to point q of city j (i != j)
vector<vector<vector<vector<double>>>> cost;

// Precompute all pairwise costs between points of different cities
void precompute_costs() {
    cost.assign(M, vector<vector<vector<double>>>(M));
    for (int i = 0; i < M; ++i) {
        for (int j = 0; j < M; ++j) {
            if (i == j) continue;
            cost[i][j].assign(n[i], vector<double>(n[j], 0.0));
            double dx = abs(city_x[i] - city_x[j]);
            if (dx == 0.0) dx = 1.0; // avoid division by zero
            for (int p = 0; p < n[i]; ++p) {
                for (int q = 0; q < n[j]; ++q) {
                    double dy = city_y[j][q] - city_y[i][p];
                    double dist = sqrt(dx*dx + dy*dy);
                    double slope = 0.0;
                    if (city_y[j][q] > city_y[i][p]) {
                        slope = (city_y[j][q] - city_y[i][p]) / dx;
                    }
                    cost[i][j][p][q] = dist_coeff * dist + slope_coeff * slope;
                }
            }
        }
    }
}

// Compute total cost of a tour given order and point selection
double compute_total_cost(const vector<int>& order, const vector<int>& point_sel) {
    double total = 0.0;
    int sz = order.size();
    for (int i = 0; i < sz; ++i) {
        int city_i = order[i];
        int city_j = order[(i+1) % sz];
        total += cost[city_i][city_j][point_sel[city_i]][point_sel[city_j]];
    }
    return total;
}

// Optimize point selection for a fixed order using DP (cycle)
double optimize_points_for_order(const vector<int>& order, vector<int>& point_sel) {
    int L = order.size();
    double best_cost = INF;
    vector<int> best_points(L);

    int start_city = order[0];
    for (int p0 = 0; p0 < n[start_city]; ++p0) {
        // dp[i][p] = min cost up to i-th city ending with point p
        vector<vector<double>> dp(L);
        vector<vector<int>> prev(L);
        for (int i = 0; i < L; ++i) {
            int ci = order[i];
            dp[i].assign(n[ci], INF);
            prev[i].assign(n[ci], -1);
        }
        dp[0][p0] = 0.0;

        // forward DP
        for (int i = 1; i < L; ++i) {
            int ci_prev = order[i-1];
            int ci_cur = order[i];
            for (int p_cur = 0; p_cur < n[ci_cur]; ++p_cur) {
                double best = INF;
                int best_prev = -1;
                for (int p_prev = 0; p_prev < n[ci_prev]; ++p_prev) {
                    double val = dp[i-1][p_prev] + cost[ci_prev][ci_cur][p_prev][p_cur];
                    if (val < best) {
                        best = val;
                        best_prev = p_prev;
                    }
                }
                dp[i][p_cur] = best;
                prev[i][p_cur] = best_prev;
            }
        }

        // close the cycle
        int last_city = order[L-1];
        double total = INF;
        int best_last = -1;
        for (int p_last = 0; p_last < n[last_city]; ++p_last) {
            double val = dp[L-1][p_last] + cost[last_city][start_city][p_last][p0];
            if (val < total) {
                total = val;
                best_last = p_last;
            }
        }

        if (total < best_cost) {
            best_cost = total;
            // backtrack
            vector<int> points(L);
            points[L-1] = best_last;
            for (int i = L-1; i > 0; --i) {
                points[i-1] = prev[i][points[i]];
            }
            points[0] = p0; // already set
            best_points = points;
        }
    }

    // assign point_sel
    for (int i = 0; i < L; ++i) {
        point_sel[order[i]] = best_points[i];
    }
    return best_cost;
}

// Greedy improvement of points for a fixed order (iterative 1-opt)
void improve_points_greedy(const vector<int>& order, vector<int>& point_sel) {
    int L = order.size();
    bool improved = true;
    while (improved) {
        improved = false;
        for (int idx = 0; idx < L; ++idx) {
            int city_i = order[idx];
            int prev_city = order[(idx-1+L)%L];
            int next_city = order[(idx+1)%L];
            double current = cost[prev_city][city_i][point_sel[prev_city]][point_sel[city_i]] +
                             cost[city_i][next_city][point_sel[city_i]][point_sel[next_city]];
            int best_p = point_sel[city_i];
            for (int p = 0; p < n[city_i]; ++p) {
                double newc = cost[prev_city][city_i][point_sel[prev_city]][p] +
                              cost[city_i][next_city][p][point_sel[next_city]];
                if (newc < current - EPS) {
                    current = newc;
                    best_p = p;
                }
            }
            if (best_p != point_sel[city_i]) {
                point_sel[city_i] = best_p;
                improved = true;
            }
        }
    }
}

// Swap two cities in the tour and locally re-optimize points for affected cities
bool try_swap_move(vector<int>& order, vector<int>& point_sel, double& current_cost) {
    int L = order.size();
    vector<pair<int,int>> pairs;
    for (int a = 0; a < L; ++a)
        for (int b = a+1; b < L; ++b)
            pairs.push_back({a, b});
    // shuffle to avoid bias
    random_device rd;
    mt19937 g(rd());
    shuffle(pairs.begin(), pairs.end(), g);

    for (auto& ab : pairs) {
        int a = ab.first, b = ab.second;
        vector<int> new_order = order;
        swap(new_order[a], new_order[b]);
        vector<int> new_point = point_sel;

        // collect affected cities: swapped cities and their neighbors
        set<int> affected;
        affected.insert(new_order[a]);
        affected.insert(new_order[b]);
        int prev_a = new_order[(a-1+L)%L];
        int next_a = new_order[(a+1)%L];
        int prev_b = new_order[(b-1+L)%L];
        int next_b = new_order[(b+1)%L];
        affected.insert(prev_a);
        affected.insert(next_a);
        affected.insert(prev_b);
        affected.insert(next_b);

        // locally re-optimize points for affected cities
        bool changed;
        int iter = 0;
        do {
            changed = false;
            for (int city : affected) {
                // find position of city in new_order
                int pos = -1;
                for (int i = 0; i < L; ++i)
                    if (new_order[i] == city) { pos = i; break; }
                int prev_city = new_order[(pos-1+L)%L];
                int next_city = new_order[(pos+1)%L];
                double cur = cost[prev_city][city][new_point[prev_city]][new_point[city]] +
                             cost[city][next_city][new_point[city]][new_point[next_city]];
                int best_p = new_point[city];
                for (int p = 0; p < n[city]; ++p) {
                    double newc = cost[prev_city][city][new_point[prev_city]][p] +
                                  cost[city][next_city][p][new_point[next_city]];
                    if (newc < cur - EPS) {
                        cur = newc;
                        best_p = p;
                    }
                }
                if (best_p != new_point[city]) {
                    new_point[city] = best_p;
                    changed = true;
                }
            }
            iter++;
        } while (changed && iter < 5);

        double new_cost = compute_total_cost(new_order, new_point);
        if (new_cost < current_cost - EPS) {
            order = new_order;
            point_sel = new_point;
            current_cost = new_cost;
            return true;
        }
    }
    return false;
}

// Perform swap-based local search
void local_search_swaps(vector<int>& order, vector<int>& point_sel) {
    double current_cost = compute_total_cost(order, point_sel);
    bool improved = true;
    while (improved) {
        improved = try_swap_move(order, point_sel, current_cost);
    }
}

// Build an initial tour using cheapest insertion heuristic
void build_tour_insertion(vector<int>& order, vector<int>& point_sel, int start_city) {
    order.clear();
    order.push_back(start_city);
    point_sel[start_city] = 0; // arbitrary point, will be optimized later

    vector<bool> used(M, false);
    used[start_city] = true;

    while ((int)order.size() < M) {
        double best_delta = INF;
        int best_city = -1;
        int best_pos = -1;
        int best_point = -1;

        for (int c = 0; c < M; ++c) {
            if (used[c]) continue;
            for (size_t idx = 0; idx <= order.size(); ++idx) {
                int cityA = order[idx % order.size()];
                int cityB = order[(idx+1) % order.size()];
                double cost_AB = cost[cityA][cityB][point_sel[cityA]][point_sel[cityB]];
                for (int p = 0; p < n[c]; ++p) {
                    double delta = cost[cityA][c][point_sel[cityA]][p] +
                                   cost[c][cityB][p][point_sel[cityB]] - cost_AB;
                    if (delta < best_delta) {
                        best_delta = delta;
                        best_city = c;
                        best_pos = idx;
                        best_point = p;
                    }
                }
            }
        }

        // Insert best_city at position best_pos
        if (best_pos == (int)order.size()) {
            order.push_back(best_city);
        } else {
            order.insert(order.begin() + best_pos + 1, best_city);
        }
        used[best_city] = true;
        point_sel[best_city] = best_point;
    }
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    double base;
    cin >> base;
    cin >> M;

    n.resize(M);
    city_x.resize(M);
    city_y.resize(M);

    for (int i = 0; i < M; ++i) {
        cin >> n[i] >> city_x[i];
        city_y[i].resize(n[i]);
        for (int j = 0; j < n[i]; ++j) {
            cin >> city_y[i][j];
        }
    }

    int D_in, S_in;
    cin >> D_in >> S_in;

    const double k = 0.6;
    dist_coeff = (1.0 - k) / D_in;
    slope_coeff = k / S_in;

    precompute_costs();

    // Best solution found
    double best_cost = INF;
    vector<int> best_order;
    vector<int> best_point_sel(M, -1);

    // Number of random restarts
    const int NUM_RESTARTS = 10;
    random_device rd;
    mt19937 gen(rd());
    uniform_int_distribution<> start_dist(0, M-1);

    for (int restart = 0; restart < NUM_RESTARTS; ++restart) {
        int start_city = start_dist(gen);
        vector<int> order;
        vector<int> point_sel(M, -1);

        // Construction
        build_tour_insertion(order, point_sel, start_city);

        // Point optimization for this order
        optimize_points_for_order(order, point_sel);

        // Local improvement
        local_search_swaps(order, point_sel);

        // Final point optimization
        double final_cost = optimize_points_for_order(order, point_sel);

        if (final_cost < best_cost) {
            best_cost = final_cost;
            best_order = order;
            best_point_sel = point_sel;
        }
    }

    // Output the best solution found
    for (size_t i = 0; i < best_order.size(); ++i) {
        int city_id = best_order[i] + 1;
        int point_idx = best_point_sel[best_order[i]] + 1;
        cout << "(" << city_id << "," << point_idx << ")";
        if (i != best_order.size() - 1)
            cout << "@";
    }
    cout << endl;

    return 0;
}