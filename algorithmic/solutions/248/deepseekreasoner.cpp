#include <bits/stdc++.h>
using namespace std;

const double INF = 1e9;
const double k = 0.6;
const double w1 = 1.0 - k;   // 0.4
const double w2 = k;         // 0.6

struct City {
    int x;
    vector<int> y;
};

double calc_edge_cost(int i, int pi, int j, int pj,
                      const vector<City>& cities,
                      const vector<vector<double>>& dx,
                      const vector<vector<double>>& inv_dx,
                      double w_dist, double w_slope) {
    double dy = cities[j].y[pj] - cities[i].y[pi];
    double dist = sqrt(dx[i][j] * dx[i][j] +
                       (cities[i].y[pi] - cities[j].y[pj]) *
                       (cities[i].y[pi] - cities[j].y[pj]));
    double slope = 0.0;
    if (dy > 0) {
        if (dx[i][j] == 0)
            slope = INF;
        else
            slope = dy * inv_dx[i][j];
    }
    return w_dist * dist + w_slope * slope;
}

void update_cost_matrix_for_city(int idx,
                                 vector<vector<double>>& cost,
                                 const vector<int>& chosen,
                                 const vector<City>& cities,
                                 const vector<vector<double>>& dx,
                                 const vector<vector<double>>& inv_dx,
                                 double w_dist, double w_slope) {
    int M = cost.size();
    for (int j = 0; j < M; ++j) {
        if (idx == j) continue;
        cost[idx][j] = calc_edge_cost(idx, chosen[idx], j, chosen[j],
                                      cities, dx, inv_dx, w_dist, w_slope);
        cost[j][idx] = calc_edge_cost(j, chosen[j], idx, chosen[idx],
                                      cities, dx, inv_dx, w_dist, w_slope);
    }
}

double tour_cost(const vector<int>& tour, const vector<vector<double>>& cost) {
    int M = tour.size();
    double total = 0.0;
    for (int i = 0; i < M; ++i) {
        int a = tour[i];
        int b = tour[(i + 1) % M];
        total += cost[a][b];
    }
    return total;
}

void point_optimization(vector<int>& tour,
                        vector<int>& chosen,
                        vector<vector<double>>& cost,
                        const vector<City>& cities,
                        const vector<vector<double>>& dx,
                        const vector<vector<double>>& inv_dx,
                        double w_dist, double w_slope) {
    int M = tour.size();
    bool changed = true;
    int iter = 0;
    while (changed && iter < 10) {
        changed = false;
        vector<int> order(M);
        iota(order.begin(), order.end(), 0);
        random_shuffle(order.begin(), order.end());
        for (int idx : order) {
            int city = tour[idx];
            int pred = tour[(idx - 1 + M) % M];
            int succ = tour[(idx + 1) % M];
            double best_val = 1e18;
            int best_p = chosen[city];
            for (int p = 0; p < (int)cities[city].y.size(); ++p) {
                double cost_pred = calc_edge_cost(pred, chosen[pred], city, p,
                                                  cities, dx, inv_dx, w_dist, w_slope);
                double cost_succ = calc_edge_cost(city, p, succ, chosen[succ],
                                                  cities, dx, inv_dx, w_dist, w_slope);
                double total = cost_pred + cost_succ;
                if (total < best_val) {
                    best_val = total;
                    best_p = p;
                }
            }
            if (best_p != chosen[city]) {
                chosen[city] = best_p;
                update_cost_matrix_for_city(city, cost, chosen,
                                            cities, dx, inv_dx, w_dist, w_slope);
                changed = true;
            }
        }
        ++iter;
    }
}

void two_opt(vector<int>& tour, const vector<vector<double>>& cost) {
    int M = tour.size();
    bool improved = true;
    while (improved) {
        improved = false;
        for (int i = 0; i < M && !improved; ++i) {
            for (int j = i + 1; j < M && !improved; ++j) {
                int a = tour[i];
                int b = tour[(i + 1) % M];
                int c = tour[j];
                int d = tour[(j + 1) % M];

                double old1 = cost[a][b];
                double old2 = cost[c][d];
                double new1 = cost[a][c];
                double new2 = cost[b][d];

                double internal_old = 0.0;
                for (int k = i + 1; k < j; ++k)
                    internal_old += cost[tour[k]][tour[k + 1]];

                double internal_new = 0.0;
                for (int k = j; k > i + 1; --k)
                    internal_new += cost[tour[k]][tour[k - 1]];

                double delta = (new1 + new2 + internal_new) - (old1 + old2 + internal_old);
                if (delta < -1e-9) {
                    reverse(tour.begin() + i + 1, tour.begin() + j + 1);
                    improved = true;
                }
            }
        }
    }
}

vector<int> greedy_tour(int start, const vector<vector<double>>& cost) {
    int M = cost.size();
    vector<bool> visited(M, false);
    vector<int> tour;
    tour.push_back(start);
    visited[start] = true;
    int cur = start;
    for (int step = 1; step < M; ++step) {
        int best = -1;
        double best_cost = 1e18;
        for (int j = 0; j < M; ++j) {
            if (!visited[j] && cost[cur][j] < best_cost) {
                best_cost = cost[cur][j];
                best = j;
            }
        }
        tour.push_back(best);
        visited[best] = true;
        cur = best;
    }
    return tour;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    double base;
    cin >> base;

    int M;
    cin >> M;

    vector<City> cities(M);
    for (int i = 0; i < M; ++i) {
        int n, x;
        cin >> n >> x;
        cities[i].x = x;
        cities[i].y.resize(n);
        for (int j = 0; j < n; ++j)
            cin >> cities[i].y[j];
    }

    double D, S;
    cin >> D >> S;
    double w_dist = w1 / D;
    double w_slope = w2 / S;

    vector<vector<double>> dx(M, vector<double>(M, 0));
    vector<vector<double>> inv_dx(M, vector<double>(M, 0));
    for (int i = 0; i < M; ++i) {
        for (int j = 0; j < M; ++j) {
            if (i == j) continue;
            double d = abs(cities[i].x - cities[j].x);
            dx[i][j] = d;
            if (d == 0)
                inv_dx[i][j] = INF;
            else
                inv_dx[i][j] = 1.0 / d;
        }
    }

    unsigned seed = chrono::high_resolution_clock::now().time_since_epoch().count();
    mt19937 rng(seed);

    double best_total = 1e18;
    vector<int> best_tour;
    vector<int> best_chosen(M);

    const int NUM_STARTS = 30;

    for (int start = 0; start < NUM_STARTS; ++start) {
        vector<int> chosen(M);
        for (int i = 0; i < M; ++i) {
            int n = cities[i].y.size();
            uniform_int_distribution<int> distr(0, n - 1);
            chosen[i] = distr(rng);
        }

        vector<vector<double>> cost(M, vector<double>(M, 0));
        for (int i = 0; i < M; ++i) {
            for (int j = 0; j < M; ++j) {
                if (i != j) {
                    cost[i][j] = calc_edge_cost(i, chosen[i], j, chosen[j],
                                                cities, dx, inv_dx, w_dist, w_slope);
                }
            }
        }

        int start_city = uniform_int_distribution<int>(0, M - 1)(rng);
        vector<int> tour = greedy_tour(start_city, cost);

        double prev_cost = tour_cost(tour, cost);
        for (int iter = 0; iter < 20; ++iter) {
            point_optimization(tour, chosen, cost, cities, dx, inv_dx, w_dist, w_slope);
            two_opt(tour, cost);
            double new_cost = tour_cost(tour, cost);
            if (abs(new_cost - prev_cost) < 1e-9) break;
            prev_cost = new_cost;
        }

        double total = tour_cost(tour, cost);
        if (total < best_total) {
            best_total = total;
            best_tour = tour;
            best_chosen = chosen;
        }
    }

    for (int i = 0; i < M; ++i) {
        int city_id = best_tour[i] + 1;
        int point_id = best_chosen[best_tour[i]] + 1;
        cout << "(" << city_id << "," << point_id << ")";
        if (i < M - 1) cout << "@";
    }
    cout << endl;

    return 0;
}