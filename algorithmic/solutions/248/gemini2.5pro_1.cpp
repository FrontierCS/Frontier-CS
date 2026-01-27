#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>
#include <iomanip>
#include <chrono>
#include <random>
#include <cfloat>

using namespace std;

// --- Data Structures ---
struct Point {
    double x, y;
};

struct City {
    int id;
    double x;
    vector<double> y_coords;
};

// --- Global Variables ---
int M;
vector<City> cities;
double D_norm, S_norm;
mt19937 rng;

// --- Helper Functions ---

Point get_point(int city_idx, int pt_idx) {
    return {cities[city_idx].x, cities[city_idx].y_coords[pt_idx]};
}

double edge_cost(const Point& p1, const Point& p2) {
    double dx = p1.x - p2.x;
    double dy = p1.y - p2.y;
    double dist = sqrt(dx * dx + dy * dy);
    double slope = 0.0;
    if (abs(dx) > 1e-9) {
        if (p2.y > p1.y) {
            slope = (p2.y - p1.y) / abs(dx);
        }
    } else if (p2.y > p1.y) {
        return DBL_MAX; // effectively infinite cost
    }
    return D_norm * dist + S_norm * slope;
}

double calculate_tour_cost(const vector<int>& tour, const vector<int>& selection) {
    double total_cost = 0;
    for (int i = 0; i < M; ++i) {
        int u_idx = tour[i];
        int v_idx = tour[(i + 1) % M];
        Point p1 = get_point(u_idx, selection[u_idx]);
        Point p2 = get_point(v_idx, selection[v_idx]);
        double cost = edge_cost(p1, p2);
        if (cost >= DBL_MAX) return DBL_MAX;
        total_cost += cost;
    }
    return total_cost;
}

// Local search: optimize point selection for a fixed tour
bool optimize_points(const vector<int>& tour, vector<int>& selection) {
    bool changed = false;
    for (int i = 0; i < M; ++i) {
        int city_idx = tour[i];
        int prev_city_idx = tour[(i - 1 + M) % M];
        int next_city_idx = tour[(i + 1) % M];

        Point prev_p = get_point(prev_city_idx, selection[prev_city_idx]);
        Point next_p = get_point(next_city_idx, selection[next_city_idx]);

        int current_best_pt_idx = selection[city_idx];
        double min_local_cost = edge_cost(prev_p, get_point(city_idx, current_best_pt_idx)) +
                                edge_cost(get_point(city_idx, current_best_pt_idx), next_p);

        for (int pt_idx = 0; pt_idx < cities[city_idx].y_coords.size(); ++pt_idx) {
            if (pt_idx == current_best_pt_idx) continue;
            Point current_p = get_point(city_idx, pt_idx);
            double local_cost = edge_cost(prev_p, current_p) + edge_cost(current_p, next_p);
            if (local_cost < min_local_cost) {
                min_local_cost = local_cost;
                current_best_pt_idx = pt_idx;
            }
        }

        if (selection[city_idx] != current_best_pt_idx) {
            selection[city_idx] = current_best_pt_idx;
            changed = true;
        }
    }
    return changed;
}

// Local search: 2-opt for tour with fixed points
bool optimize_tour_2opt(vector<int>& tour, const vector<int>& selection) {
    for (int i = 0; i < M; ++i) {
        for (int j = i + 2; j < M; ++j) {
             if (i == 0 && j == M - 1) continue;

            int u1_idx = tour[i];
            int v1_idx = tour[i + 1];
            int u2_idx = tour[j];
            int v2_idx = tour[(j + 1) % M];

            Point p_u1 = get_point(u1_idx, selection[u1_idx]);
            Point p_v1 = get_point(v1_idx, selection[v1_idx]);
            Point p_u2 = get_point(u2_idx, selection[u2_idx]);
            Point p_v2 = get_point(v2_idx, selection[v2_idx]);

            double current_edges_cost = edge_cost(p_u1, p_v1) + edge_cost(p_u2, p_v2);
            double new_edges_cost = edge_cost(p_u1, p_u2) + edge_cost(p_v1, p_v2);

            if (new_edges_cost < current_edges_cost) {
                reverse(tour.begin() + i + 1, tour.begin() + j + 1);
                return true; // First improvement
            }
        }
    }
    return false;
}

void perturb_tour(vector<int>& tour) {
    int len = M / 4 + 1;
    uniform_int_distribution<int> dist_idx(0, M - len);
    int start1 = dist_idx(rng);
    int start2 = dist_idx(rng);

    if (abs(start1 - start2) < len) {
        uniform_int_distribution<int> dist_len(2, M / 10 + 2);
        uniform_int_distribution<int> dist_pos(0, M - 1);
        int l = dist_len(rng);
        int p = dist_pos(rng);
        if (p + l > M) p = M - l;
        shuffle(tour.begin() + p, tour.begin() + p + l, rng);
    } else {
        if (start1 > start2) swap(start1, start2);
        vector<int> segment;
        for (int i = start1; i < start1 + len; ++i) segment.push_back(tour[i]);
        tour.erase(tour.begin() + start1, tour.begin() + start1 + len);
        tour.insert(tour.begin() + start2 - len, segment.begin(), segment.end());
    }
}


int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    cout << fixed << setprecision(10);
    rng.seed(chrono::steady_clock::now().time_since_epoch().count());

    double base;
    cin >> base;
    cin >> M;
    cities.resize(M);
    for (int i = 0; i < M; ++i) {
        cities[i].id = i + 1;
        int n;
        cin >> n >> cities[i].x;
        cities[i].y_coords.resize(n);
        for (int j = 0; j < n; ++j) {
            cin >> cities[i].y_coords[j];
        }
    }
    double D_orig, S_orig;
    cin >> D_orig >> S_orig;
    
    double k = 0.6;
    D_norm = (1.0 - k) / D_orig;
    S_norm = k / S_orig;

    // --- Initial Solution ---
    vector<int> best_selection(M);
    for (int i = 0; i < M; ++i) {
        best_selection[i] = cities[i].y_coords.size() / 2;
    }

    vector<int> best_tour(M);
    vector<bool> visited(M, false);
    best_tour[0] = 0;
    visited[0] = true;
    for (int i = 1; i < M; ++i) {
        int last_city_idx = best_tour[i - 1];
        Point last_p = get_point(last_city_idx, best_selection[last_city_idx]);
        
        int next_city_idx = -1;
        double min_dist_sq = DBL_MAX;

        for (int j = 0; j < M; ++j) {
            if (!visited[j]) {
                Point current_p = get_point(j, best_selection[j]);
                double dx = last_p.x - current_p.x;
                double dy = last_p.y - current_p.y;
                double dist_sq = dx * dx + dy * dy;
                if (dist_sq < min_dist_sq) {
                    min_dist_sq = dist_sq;
                    next_city_idx = j;
                }
            }
        }
        best_tour[i] = next_city_idx;
        visited[next_city_idx] = true;
    }

    double best_cost = calculate_tour_cost(best_tour, best_selection);

    // --- Iterated Local Search ---
    auto start_time = chrono::high_resolution_clock::now();
    
    auto current_tour = best_tour;
    auto current_selection = best_selection;
    int no_improve_count = 0;
    
    while (chrono::duration_cast<chrono::milliseconds>(chrono::high_resolution_clock::now() - start_time).count() < 14800) {
        
        bool changed = true;
        while(changed) {
            changed = false;
            if (optimize_points(current_tour, current_selection)) changed = true;
            if (optimize_tour_2opt(current_tour, current_selection)) changed = true;
        }

        double current_cost = calculate_tour_cost(current_tour, current_selection);
        
        if (current_cost < best_cost) {
            best_cost = current_cost;
            best_tour = current_tour;
            best_selection = current_selection;
            no_improve_count = 0;
        } else {
            no_improve_count++;
        }

        current_tour = best_tour;
        current_selection = best_selection;
        
        if(no_improve_count > 0){
            perturb_tour(current_tour);
        }
        if (no_improve_count > 5) { // Reset to best and do a big perturbation
            current_tour = best_tour;
            current_selection = best_selection;
            
            uniform_int_distribution<int> dist_len(M/5, M/3);
            uniform_int_distribution<int> dist_pos(0, M-1);
            int len = dist_len(rng);
            int pos = dist_pos(rng);
            if (pos+len > M) pos = M-len;
            shuffle(current_tour.begin()+pos, current_tour.begin()+pos+len, rng);
            no_improve_count = 0;
        }
    }
    
    // --- Output ---
    for (int i = 0; i < M; ++i) {
        int city_idx = best_tour[i];
        int pt_idx = best_selection[city_idx];
        cout << "(" << cities[city_idx].id << "," << pt_idx + 1 << ")";
        if (i < M - 1) {
            cout << "@";
        }
    }
    cout << endl;

    return 0;
}