/*
    Solution for AHC005 - Automated Patrols
    Approach: Randomized Greedy with Multiple Restarts
*/

#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <tuple>
#include <algorithm>
#include <cmath>
#include <ctime>
#include <random>

using namespace std;

// Global variables
int N;
int si, sj;
vector<string> grid;
int weights[70][70];

struct Segment {
    int id;
    bool is_horz; 
    vector<pair<int,int>> cells;
};

vector<Segment> segments;
int seg_map[70][70][2]; // [r][c][0=vert, 1=horz] -> seg_id
int num_segments = 0;

// Dijkstra structures
int dist_map[70][70];
pair<int,int> parent[70][70];
const int INF = 1e9;

// Random number generator
mt19937 rng(12345);

// Parse grid into horizontal and vertical segments
void parse_segments() {
    num_segments = 0;
    // Initialize map
    for(int i=0; i<N; ++i) 
        for(int j=0; j<N; ++j) {
            seg_map[i][j][0] = -1;
            seg_map[i][j][1] = -1;
        }

    // Vertical segments
    for(int j=0; j<N; ++j) {
        for(int i=0; i<N; ++i) {
            if(grid[i][j] != '#') {
                vector<pair<int,int>> cells;
                while(i < N && grid[i][j] != '#') {
                    cells.push_back({i, j});
                    i++;
                }
                Segment s; s.id = num_segments; s.is_horz = false; s.cells = cells;
                segments.push_back(s);
                for(auto p : cells) seg_map[p.first][p.second][0] = num_segments;
                num_segments++;
            }
        }
    }
    // Horizontal segments
    for(int i=0; i<N; ++i) {
        for(int j=0; j<N; ++j) {
            if(grid[i][j] != '#') {
                vector<pair<int,int>> cells;
                while(j < N && grid[i][j] != '#') {
                    cells.push_back({i, j});
                    j++;
                }
                Segment s; s.id = num_segments; s.is_horz = true; s.cells = cells;
                segments.push_back(s);
                for(auto p : cells) seg_map[p.first][p.second][1] = num_segments;
                num_segments++;
            }
        }
    }
}

// Reconstruct path string from parent array
string get_path_string(int tr, int tc) {
    string path = "";
    int cr = tr, cc = tc;
    while(true) {
        auto p = parent[cr][cc];
        int pr = p.first;
        int pc = p.second;
        if(pr == -1) break;
        
        if(cr == pr + 1) path += 'D';
        else if(cr == pr - 1) path += 'U';
        else if(cc == pc + 1) path += 'R';
        else if(cc == pc - 1) path += 'L';
        
        cr = pr; cc = pc;
    }
    reverse(path.begin(), path.end());
    return path;
}

// Dijkstra's algorithm from a starting point
void run_dijkstra(int start_r, int start_c) {
    for(int i=0; i<N; ++i) 
        for(int j=0; j<N; ++j) 
            dist_map[i][j] = INF;
            
    // min-heap: (dist, r, c)
    priority_queue<tuple<int,int,int>, vector<tuple<int,int,int>>, greater<tuple<int,int,int>>> pq;
    
    dist_map[start_r][start_c] = 0;
    parent[start_r][start_c] = {-1, -1};
    pq.push({0, start_r, start_c});
    
    int dr[] = {-1, 1, 0, 0};
    int dc[] = {0, 0, -1, 1};
    
    while(!pq.empty()) {
        auto [d, r, c] = pq.top();
        pq.pop();
        
        if(d > dist_map[r][c]) continue;
        
        for(int i=0; i<4; ++i) {
            int nr = r + dr[i];
            int nc = c + dc[i];
            
            if(nr >= 0 && nr < N && nc >= 0 && nc < N && grid[nr][nc] != '#') {
                int w = weights[nr][nc]; // cost to enter nr, nc
                if(dist_map[r][c] + w < dist_map[nr][nc]) {
                    dist_map[nr][nc] = dist_map[r][c] + w;
                    parent[nr][nc] = {r, c};
                    pq.push({dist_map[nr][nc], nr, nc});
                }
            }
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if(!(cin >> N >> si >> sj)) return 0;
    grid.resize(N);
    for(int i=0; i<N; ++i) {
        cin >> grid[i];
        for(int j=0; j<N; ++j) {
            if(isdigit(grid[i][j])) weights[i][j] = grid[i][j] - '0';
            else weights[i][j] = 0;
        }
    }
    
    parse_segments();
    
    double time_limit = 2.85; // slightly under 3s
    clock_t start_time = clock();
    
    string best_route = "";
    long long min_route_cost = -1;
    
    // Multiple iterations to find better solutions via randomized greedy
    while( (double)(clock() - start_time) / CLOCKS_PER_SEC < time_limit ) {
        int cur_r = si;
        int cur_c = sj;
        string current_route = "";
        long long current_cost = 0;
        
        vector<bool> covered(num_segments, false);
        int covered_cnt = 0;
        
        // Mark segments visible from start
        int s1 = seg_map[cur_r][cur_c][0];
        int s2 = seg_map[cur_r][cur_c][1];
        if(s1 != -1 && !covered[s1]) { covered[s1] = true; covered_cnt++; }
        if(s2 != -1 && !covered[s2]) { covered[s2] = true; covered_cnt++; }
        
        // Greedy loop
        while(covered_cnt < num_segments) {
            // Check time inside loop
            if ((double)(clock() - start_time) / CLOCKS_PER_SEC > time_limit) break;

            // Calculate distances to all reachable cells
            run_dijkstra(cur_r, cur_c);
            
            // Generate candidates
            // A candidate is a road cell that, if visited, covers at least one new segment.
            // We score them by: distance / (gain ^ K) * random_factor
            vector<tuple<double, int, int>> candidates;
            candidates.reserve(2000); // approx
            
            for(int i=0; i<N; ++i) {
                for(int j=0; j<N; ++j) {
                    if(grid[i][j] == '#' || dist_map[i][j] == INF) continue;
                    
                    int gain = 0;
                    int id1 = seg_map[i][j][0];
                    int id2 = seg_map[i][j][1];
                    
                    if(id1 != -1 && !covered[id1]) gain++;
                    if(id2 != -1 && !covered[id2]) gain++;
                    
                    if(gain > 0) {
                        double cost = dist_map[i][j];
                        // Randomization: 0.7 to 1.3
                        double r_val = uniform_real_distribution<>(0.7, 1.3)(rng);
                        
                        // Heuristic score (lower is better)
                        // Prefer high gain, low cost.
                        double score = cost / pow(gain, 1.5) * r_val;
                        
                        candidates.emplace_back(score, i, j);
                    }
                }
            }
            
            if(candidates.empty()) break; 
            
            // Pick the best candidate
            auto best_it = min_element(candidates.begin(), candidates.end());
            auto [sc, best_r, best_c] = *best_it;
            
            // Update route
            string path_seg = get_path_string(best_r, best_c);
            current_route += path_seg;
            current_cost += dist_map[best_r][best_c];
            
            cur_r = best_r;
            cur_c = best_c;
            
            // Update coverage
            int nid1 = seg_map[cur_r][cur_c][0];
            int nid2 = seg_map[cur_r][cur_c][1];
            if(nid1 != -1 && !covered[nid1]) { covered[nid1] = true; covered_cnt++; }
            if(nid2 != -1 && !covered[nid2]) { covered[nid2] = true; covered_cnt++; }
        }
        
        // Break if timeout happened inside loop
        if ((double)(clock() - start_time) / CLOCKS_PER_SEC > time_limit) break;
        
        // Return to start
        run_dijkstra(cur_r, cur_c);
        if(dist_map[si][sj] != INF) {
             current_route += get_path_string(si, sj);
             current_cost += dist_map[si][sj];
        } else {
            // Should be reachable
            continue;
        }
        
        // Update best solution
        if(min_route_cost == -1 || current_cost < min_route_cost) {
            min_route_cost = current_cost;
            best_route = current_route;
        }
    }
    
    cout << best_route << endl;
    return 0;
}