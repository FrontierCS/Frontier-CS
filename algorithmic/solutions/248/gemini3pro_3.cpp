#include <iostream>
#include <vector>
#include <cmath>
#include <algorithm>
#include <iomanip>
#include <ctime>
#include <cstdlib>
#include <limits>

using namespace std;

struct Point {
    int city_id; // 1-based from input order
    int point_idx; // 1-based index within city
    int x, y;
    int global_id;
};

struct City {
    int id;
    int n;
    int x;
    vector<int> point_global_ids;
};

int M;
double D_in, S_in;
const double k = 0.6;
double W_d, W_s;

vector<City> cities;
vector<Point> all_points;
// Cost matrix: [global_id_from][global_id_to]
vector<vector<double>> adj_cost;

double calc_dist(const Point& a, const Point& b) {
    double dx = (double)a.x - b.x;
    double dy = (double)a.y - b.y;
    return sqrt(dx*dx + dy*dy);
}

double calc_slope_cost(const Point& a, const Point& b) {
    if (b.y <= a.y) return 0.0;
    int dx_int = abs(a.x - b.x);
    // Handle vertical climb (same city or same x)
    if (dx_int == 0) {
         // Vertical climb cost penalty. Assuming a small epsilon for run.
         // Using 0.1 as a proxy for very steep slope
         return (double)(b.y - a.y) / 0.1; 
    }
    return (double)(b.y - a.y) / (double)dx_int;
}

void precompute_costs() {
    int num_points = all_points.size();
    adj_cost.assign(num_points, vector<double>(num_points));
    for (int i = 0; i < num_points; ++i) {
        for (int j = 0; j < num_points; ++j) {
            if (i == j) {
                adj_cost[i][j] = 0;
                continue;
            }
            double d = calc_dist(all_points[i], all_points[j]);
            double s = calc_slope_cost(all_points[i], all_points[j]);
            adj_cost[i][j] = W_d * d + W_s * s;
        }
    }
}

// DP to optimize landing points for a fixed city sequence
double optimize_choices(const vector<int>& cities_seq, vector<int>& best_choices) {
    int first_city_idx = cities_seq[0];
    int n_first = cities[first_city_idx].n;
    
    double global_min_cost = 1e18;
    vector<int> global_best_p_indices(M); 
    
    for (int start_p_local = 0; start_p_local < n_first; ++start_p_local) {
        int start_node = cities[first_city_idx].point_global_ids[start_p_local];
        
        int curr_city_idx = cities_seq[1];
        int n_curr = cities[curr_city_idx].n;
        vector<double> dp(n_curr);
        vector<vector<int>> parent(M, vector<int>()); 
        
        for (int j = 0; j < n_curr; ++j) {
            int curr_node = cities[curr_city_idx].point_global_ids[j];
            dp[j] = adj_cost[start_node][curr_node];
        }
        
        for(int i=1; i<M; ++i) {
             parent[i].resize(cities[cities_seq[i]].n);
        }
        
        for (int i = 2; i < M; ++i) {
            int next_city_idx = cities_seq[i];
            int n_next = cities[next_city_idx].n;
            int prev_c_idx = cities_seq[i-1];
            int n_prev = cities[prev_c_idx].n;
            
            vector<double> next_dp(n_next, 1e18);
            
            for (int j = 0; j < n_next; ++j) {
                int next_node = cities[next_city_idx].point_global_ids[j];
                for (int k = 0; k < n_prev; ++k) {
                    int prev_node = cities[prev_c_idx].point_global_ids[k];
                    double val = dp[k] + adj_cost[prev_node][next_node];
                    if (val < next_dp[j]) {
                        next_dp[j] = val;
                        parent[i][j] = k;
                    }
                }
            }
            dp = next_dp;
        }
        
        int last_city_idx = cities_seq[M-1];
        int n_last = cities[last_city_idx].n;
        double min_cycle_cost = 1e18;
        int best_last_p = -1;
        
        for (int k = 0; k < n_last; ++k) {
            int last_node = cities[last_city_idx].point_global_ids[k];
            double val = dp[k] + adj_cost[last_node][start_node];
            if (val < min_cycle_cost) {
                min_cycle_cost = val;
                best_last_p = k;
            }
        }
        
        if (min_cycle_cost < global_min_cost) {
            global_min_cost = min_cycle_cost;
            global_best_p_indices[0] = start_node;
            int curr_p = best_last_p;
            for (int i = M - 1; i >= 1; --i) {
                global_best_p_indices[i] = cities[cities_seq[i]].point_global_ids[curr_p];
                curr_p = parent[i][curr_p];
            }
        }
    }
    
    for (int i = 0; i < M; ++i) {
        best_choices[cities_seq[i]] = global_best_p_indices[i];
    }
    
    return global_min_cost;
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    srand(time(0));

    double base;
    if (!(cin >> base)) return 0;
    if (!(cin >> M)) return 0;
    
    cities.resize(M);
    int gid_counter = 0;
    
    for (int i = 0; i < M; ++i) {
        cities[i].id = i;
        cin >> cities[i].n >> cities[i].x;
        for (int j = 0; j < cities[i].n; ++j) {
            int y;
            cin >> y;
            Point p;
            p.city_id = i + 1; 
            p.point_idx = j + 1; 
            p.x = cities[i].x;
            p.y = y;
            p.global_id = gid_counter++;
            cities[i].point_global_ids.push_back(p.global_id);
            all_points.push_back(p);
        }
    }
    cin >> D_in >> S_in;
    
    W_d = (1.0 - k) / D_in;
    W_s = k / S_in;
    
    precompute_costs();
    
    vector<int> path(M);
    for (int i = 0; i < M; ++i) path[i] = i;
    random_shuffle(path.begin(), path.end());
    
    vector<int> current_choices(M);
    for (int i = 0; i < M; ++i) {
        current_choices[i] = cities[i].point_global_ids[rand() % cities[i].n];
    }
    
    double current_cost = 0;
    for (int i = 0; i < M; ++i) {
        int u = current_choices[path[i]];
        int v = current_choices[path[(i + 1) % M]];
        current_cost += adj_cost[u][v];
    }
    
    double best_cost = current_cost;
    vector<int> best_path = path;
    vector<int> best_choices_map = current_choices;
    
    double start_T = 100.0;
    double end_T = 1e-4;
    double T = start_T;
    
    clock_t start_time = clock();
    double time_limit = 14.8;
    int iter = 0;
    
    while (true) {
        iter++;
        if ((iter & 255) == 0) {
            double elapsed = (double)(clock() - start_time) / CLOCKS_PER_SEC;
            if (elapsed > time_limit) break;
            double progress = elapsed / time_limit;
            T = start_T * pow(end_T / start_T, progress);
        }
        
        int move_type = rand() % 100;
        double delta = 0;
        
        if (move_type < 50) { 
            // Change point for a random city
            int path_idx = rand() % M;
            int city_idx = path[path_idx];
            int n_opts = cities[city_idx].n;
            if (n_opts <= 1) continue;
            
            int old_point_gid = current_choices[city_idx];
            int new_point_local = rand() % n_opts;
            int new_point_gid = cities[city_idx].point_global_ids[new_point_local];
            if (new_point_gid == old_point_gid) {
                 new_point_gid = cities[city_idx].point_global_ids[(new_point_local + 1) % n_opts];
            }
            
            int prev_city = path[(path_idx + M - 1) % M];
            int next_city = path[(path_idx + 1) % M];
            int prev_pt = current_choices[prev_city];
            int next_pt = current_choices[next_city];
            
            delta -= adj_cost[prev_pt][old_point_gid];
            delta -= adj_cost[old_point_gid][next_pt];
            delta += adj_cost[prev_pt][new_point_gid];
            delta += adj_cost[new_point_gid][next_pt];
            
            if (delta < 0 || exp(-delta / T) > (double)rand() / RAND_MAX) {
                current_cost += delta;
                current_choices[city_idx] = new_point_gid;
                if (current_cost < best_cost) {
                    best_cost = current_cost;
                    best_path = path;
                    best_choices_map = current_choices;
                }
            }
        } 
        else if (move_type < 70) {
            // Swap cities
            int i = rand() % M;
            int j = rand() % M;
            if (i == j) continue;
            
            int c1 = path[i];
            int c2 = path[j];
            int p_c1 = current_choices[c1];
            int p_c2 = current_choices[c2];
            
            int i_prev = (i + M - 1) % M;
            int i_next = (i + 1) % M;
            int j_prev = (j + M - 1) % M;
            int j_next = (j + 1) % M;
            
            double old_edges = 0;
            double new_edges = 0;
            
            if (i_next == j) { 
                int prev = current_choices[path[i_prev]];
                int next = current_choices[path[j_next]];
                old_edges += adj_cost[prev][p_c1] + adj_cost[p_c1][p_c2] + adj_cost[p_c2][next];
                new_edges += adj_cost[prev][p_c2] + adj_cost[p_c2][p_c1] + adj_cost[p_c1][next];
            } else if (j_next == i) { 
                 int prev = current_choices[path[j_prev]];
                 int next = current_choices[path[i_next]];
                 old_edges += adj_cost[prev][p_c2] + adj_cost[p_c2][p_c1] + adj_cost[p_c1][next];
                 new_edges += adj_cost[prev][p_c1] + adj_cost[p_c1][p_c2] + adj_cost[p_c2][next];
            } else {
                int p_i_prev = current_choices[path[i_prev]];
                int p_i_next = current_choices[path[i_next]];
                int p_j_prev = current_choices[path[j_prev]];
                int p_j_next = current_choices[path[j_next]];
                
                old_edges += adj_cost[p_i_prev][p_c1] + adj_cost[p_c1][p_i_next];
                old_edges += adj_cost[p_j_prev][p_c2] + adj_cost[p_c2][p_j_next];
                
                new_edges += adj_cost[p_i_prev][p_c2] + adj_cost[p_c2][p_i_next];
                new_edges += adj_cost[p_j_prev][p_c1] + adj_cost[p_c1][p_j_next];
            }
            
            delta = new_edges - old_edges;
            
            if (delta < 0 || exp(-delta / T) > (double)rand() / RAND_MAX) {
                current_cost += delta;
                swap(path[i], path[j]);
                if (current_cost < best_cost) {
                    best_cost = current_cost;
                    best_path = path;
                    best_choices_map = current_choices;
                }
            }
        } 
        else {
            // Reverse segment
            int i = rand() % M;
            int j = rand() % M;
            if (i == j) continue;
            
            int len = 2 + rand() % (M - 2); 
            int start = i;
            int end = (i + len - 1) % M;
            
            double old_seg_cost = 0;
            double new_seg_cost = 0;
            
            int p_before = current_choices[path[(start + M - 1) % M]];
            int p_after = current_choices[path[(end + 1) % M]];
            
            int curr = start;
            int steps = 0;
            vector<int> segment_nodes; 
            segment_nodes.reserve(len);
            
            while (steps < len) {
                segment_nodes.push_back(current_choices[path[curr]]);
                curr = (curr + 1) % M;
                steps++;
            }
            
            old_seg_cost += adj_cost[p_before][segment_nodes[0]];
            for (size_t k = 0; k < segment_nodes.size() - 1; ++k) {
                old_seg_cost += adj_cost[segment_nodes[k]][segment_nodes[k+1]];
            }
            old_seg_cost += adj_cost[segment_nodes.back()][p_after];
            
            new_seg_cost += adj_cost[p_before][segment_nodes.back()];
            for (int k = (int)segment_nodes.size() - 1; k > 0; --k) {
                new_seg_cost += adj_cost[segment_nodes[k]][segment_nodes[k-1]];
            }
            new_seg_cost += adj_cost[segment_nodes[0]][p_after];
            
            delta = new_seg_cost - old_seg_cost;
            
            if (delta < 0 || exp(-delta / T) > (double)rand() / RAND_MAX) {
                current_cost += delta;
                for(int k=0; k < len/2; ++k) {
                    int idx1 = (start + k) % M;
                    int idx2 = (start + len - 1 - k) % M;
                    swap(path[idx1], path[idx2]);
                }
                if (current_cost < best_cost) {
                    best_cost = current_cost;
                    best_path = path;
                    best_choices_map = current_choices;
                }
            }
        }
    }
    
    optimize_choices(best_path, best_choices_map);
    
    bool first = true;
    for (int i = 0; i < M; ++i) {
        if (!first) cout << "@";
        int city_idx = best_path[i];
        int point_gid = best_choices_map[city_idx];
        const Point& p = all_points[point_gid];
        cout << "(" << p.city_id << "," << p.point_idx << ")";
        first = false;
    }
    cout << endl;
    
    return 0;
}