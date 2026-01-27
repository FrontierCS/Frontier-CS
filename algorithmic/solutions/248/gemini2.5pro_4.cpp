#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>
#include <random>
#include <chrono>
#include <iomanip>

using namespace std;

struct Point {
    int x, y;
    int city_id;
    int lp_id;
};

int M;
vector<vector<Point>> cities;
double D_param, S_param;
mt19937 rng(chrono::steady_clock::now().time_since_epoch().count());

double dist(const Point& a, const Point& b) {
    long long dx = a.x - b.x;
    long long dy = a.y - b.y;
    return sqrt(dx * dx + dy * dy);
}

double slope(const Point& a, const Point& b) {
    if (a.x == b.x) {
        return (b.y > a.y) ? 1e18 : 0.0;
    }
    return max(0.0, (double)(b.y - a.y) / abs(a.x - b.x));
}

double edge_cost(const Point& a, const Point& b) {
    return D_param * dist(a, b) + S_param * slope(a, b);
}

Point get_point_from_indices(int city_idx, int lp_idx) {
    return cities[city_idx][lp_idx];
}

Point get_point_from_tour(const vector<int>& tour, const vector<int>& choices, int tour_idx) {
    int city_idx = tour[tour_idx];
    int lp_idx = choices[city_idx];
    return cities[city_idx][lp_idx];
}

double total_cost(const vector<int>& tour, const vector<int>& choices) {
    double total = 0.0;
    for (int i = 0; i < M; ++i) {
        Point p1 = get_point_from_tour(tour, choices, i);
        Point p2 = get_point_from_tour(tour, choices, (i + 1) % M);
        total += edge_cost(p1, p2);
    }
    return total;
}

double calculate_2_opt_delta(const vector<int>& tour, const vector<int>& choices, int i, int j) {
    Point pi_prev = get_point_from_tour(tour, choices, (i - 1 + M) % M);
    Point pi = get_point_from_tour(tour, choices, i);
    Point pj = get_point_from_tour(tour, choices, j);
    Point pj_next = get_point_from_tour(tour, choices, (j + 1) % M);
    return edge_cost(pi_prev, pj) + edge_cost(pi, pj_next) - (edge_cost(pi_prev, pi) + edge_cost(pj, pj_next));
}

double calculate_lp_change_delta(const vector<int>& tour, const vector<int>& city_pos, const vector<int>& choices, int city_idx, int new_lp_idx) {
    int tour_idx = city_pos[city_idx];
    Point p_prev = get_point_from_tour(tour, choices, (tour_idx - 1 + M) % M);
    Point p_next = get_point_from_tour(tour, choices, (tour_idx + 1) % M);
    int old_lp_idx = choices[city_idx];
    Point p_old = get_point_from_indices(city_idx, old_lp_idx);
    Point p_new = get_point_from_indices(city_idx, new_lp_idx);
    return edge_cost(p_prev, p_new) + edge_cost(p_new, p_next) - (edge_cost(p_prev, p_old) + edge_cost(p_old, p_next));
}

double calculate_swap_delta(const vector<int>& tour, const vector<int>& choices, int i, int j) {
    if ((i + 1) % M == j) { // Adjacent
        Point pi_prev = get_point_from_tour(tour, choices, (i - 1 + M) % M);
        Point pi = get_point_from_tour(tour, choices, i);
        Point pj = get_point_from_tour(tour, choices, j);
        Point pj_next = get_point_from_tour(tour, choices, (j + 1) % M);
        return edge_cost(pi_prev, pj) + edge_cost(pj, pi) + edge_cost(pi, pj_next) - (edge_cost(pi_prev, pi) + edge_cost(pi, pj) + edge_cost(pj, pj_next));
    } else { // Non-adjacent
        Point pi_prev = get_point_from_tour(tour, choices, (i - 1 + M) % M);
        Point pi = get_point_from_tour(tour, choices, i);
        Point pi_next = get_point_from_tour(tour, choices, (i + 1) % M);
        Point pj_prev = get_point_from_tour(tour, choices, (j - 1 + M) % M);
        Point pj = get_point_from_tour(tour, choices, j);
        Point pj_next = get_point_from_tour(tour, choices, (j + 1) % M);
        return edge_cost(pi_prev, pj) + edge_cost(pj, pi_next) + edge_cost(pj_prev, pi) + edge_cost(pi, pj_next) - (edge_cost(pi_prev, pi) + edge_cost(pi, pi_next) + edge_cost(pj_prev, pj) + edge_cost(pj, pj_next));
    }
}

void solve() {
    double base;
    cin >> base >> M;
    cities.resize(M);
    vector<pair<int, int>> x_coords;
    for (int i = 0; i < M; ++i) {
        int n, x;
        cin >> n >> x;
        cities[i].resize(n);
        x_coords.push_back({x, i});
        for (int j = 0; j < n; ++j) {
            cities[i][j].city_id = i + 1;
            cities[i][j].lp_id = j + 1;
            cities[i][j].x = x;
            cin >> cities[i][j].y;
        }
    }
    cin >> D_param >> S_param;

    vector<int> tour(M);
    sort(x_coords.begin(), x_coords.end());
    for(int i = 0; i < M; ++i) tour[i] = x_coords[i].second;
    
    vector<int> choices(M);
    for (int i = 0; i < M; ++i) {
        int best_lp = 0;
        for (size_t j = 1; j < cities[i].size(); ++j) {
            if (cities[i][j].y < cities[i][best_lp].y) best_lp = j;
        }
        choices[i] = best_lp;
    }
    
    vector<int> city_pos(M);
    for(int i=0; i<M; ++i) city_pos[tour[i]] = i;

    double current_cost = total_cost(tour, choices);
    vector<int> best_tour = tour;
    vector<int> best_choices = choices;
    double best_cost = current_cost;

    double avg_delta = 0;
    int samples = 1000;
    int accepted_samples = 0;
    for (int i = 0; i < samples; ++i) {
        int r1 = uniform_int_distribution<int>(0, M - 1)(rng);
        int r2 = uniform_int_distribution<int>(0, M - 1)(rng);
        if (r1 == r2) continue;
        if (r1 > r2) swap(r1, r2);
        if (r1 == 0 && r2 == M - 1) continue;
        double delta = calculate_2_opt_delta(tour, choices, r1, r2);
        if (delta > 0) {
            avg_delta += delta;
            accepted_samples++;
        }
    }
    if (accepted_samples > 0) avg_delta /= accepted_samples;
    else avg_delta = 1.0;
    
    double T = -avg_delta / log(0.5);
    double alpha = 0.999998;

    auto start_time = chrono::steady_clock::now();
    int time_limit_ms = 14800;
    uniform_real_distribution<double> u_dist(0.0, 1.0);

    while (chrono::duration_cast<chrono::milliseconds>(chrono::steady_clock::now() - start_time).count() < time_limit_ms) {
        int move_type = uniform_int_distribution<int>(0, 99)(rng);

        if (move_type < 40) { // 2-opt
            int i = uniform_int_distribution<int>(0, M-1)(rng);
            int j = uniform_int_distribution<int>(0, M-1)(rng);
            if (i == j) continue;
            if (i > j) swap(i, j);
            if (i == 0 && j == M - 1) continue;

            double delta = calculate_2_opt_delta(tour, choices, i, j);
            if (delta < 0 || u_dist(rng) < exp(-delta / T)) {
                current_cost += delta;
                reverse(tour.begin() + i, tour.begin() + j + 1);
                for (int k = i; k <= j; ++k) city_pos[tour[k]] = k;
                if (current_cost < best_cost) { best_cost = current_cost; best_tour = tour; best_choices = choices; }
            }
        } else if (move_type < 80) { // change landing point
            int city_idx = uniform_int_distribution<int>(0, M - 1)(rng);
            if (cities[city_idx].size() <= 1) continue;
            int new_lp_idx = uniform_int_distribution<int>(0, cities[city_idx].size() - 1)(rng);
            if (new_lp_idx == choices[city_idx]) continue;
            
            double delta = calculate_lp_change_delta(tour, city_pos, choices, city_idx, new_lp_idx);
            if (delta < 0 || u_dist(rng) < exp(-delta / T)) {
                current_cost += delta;
                choices[city_idx] = new_lp_idx;
                if (current_cost < best_cost) { best_cost = current_cost; best_tour = tour; best_choices = choices; }
            }
        } else { // swap cities
            int i = uniform_int_distribution<int>(0, M - 1)(rng);
            int j = uniform_int_distribution<int>(0, M - 1)(rng);
            if (i == j) continue;
            if (i > j) swap(i, j);

            double delta = calculate_swap_delta(tour, choices, i, j);
            if (delta < 0 || u_dist(rng) < exp(-delta / T)) {
                current_cost += delta;
                int c1 = tour[i], c2 = tour[j];
                swap(tour[i], tour[j]); city_pos[c1] = j; city_pos[c2] = i;
                if (current_cost < best_cost) { best_cost = current_cost; best_tour = tour; best_choices = choices; }
            }
        }
        T *= alpha;
    }

    for (int i = 0; i < M; ++i) {
        int city_idx = best_tour[i];
        int lp_idx = best_choices[city_idx];
        cout << "(" << cities[city_idx][lp_idx].city_id << "," << cities[city_idx][lp_idx].lp_id << ")";
        if (i < M - 1) cout << "@";
    }
    cout << endl;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    solve();
    return 0;
}