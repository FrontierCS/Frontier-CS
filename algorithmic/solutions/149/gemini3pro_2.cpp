#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <tuple>
#include <algorithm>
#include <cmath>

using namespace std;

// Grid dimensions
const int N = 30;

// Estimated weights
// h[i][j] is the weight of the horizontal edge between (i, j) and (i, j+1)
// Dimensions: 30 rows, 29 columns of edges
double h[N][N-1]; 

// v[i][j] is the weight of the vertical edge between (i, j) and (i+1, j)
// Dimensions: 29 rows of edges, 30 columns
double v[N-1][N]; 

struct Edge {
    int to_r, to_c;
    char dir; // 'U', 'D', 'L', 'R'
    int type; // 0 for horizontal, 1 for vertical
    int w_r, w_c; // indices in h or v array
};

vector<Edge> adj[N][N];

// Initialize graph and weights
void init() {
    for(int i=0; i<N; ++i) {
        for(int j=0; j<N; ++j) {
            // Up
            if(i > 0) adj[i][j].push_back({i-1, j, 'U', 1, i-1, j});
            // Down
            if(i < N-1) adj[i][j].push_back({i+1, j, 'D', 1, i, j});
            // Left
            if(j > 0) adj[i][j].push_back({i, j-1, 'L', 0, i, j-1});
            // Right
            if(j < N-1) adj[i][j].push_back({i, j+1, 'R', 0, i, j});
        }
    }
    // Initialize estimates to expected mean (around 5000 is a safe initial guess)
    for(int i=0; i<N; ++i) 
        for(int j=0; j<N-1; ++j) h[i][j] = 5000.0;
    for(int i=0; i<N-1; ++i) 
        for(int j=0; j<N; ++j) v[i][j] = 5000.0;
}

struct State {
    double dist;
    int r, c;
    bool operator>(const State& o) const { return dist > o.dist; }
};

pair<int,int> parent_node[N][N];
double dist_map[N][N];

// Dijkstra's algorithm to find shortest path based on current weights
string get_path(int si, int sj, int ti, int tj, vector<tuple<int,int,int>>& path_edges) {
    for(int i=0; i<N; ++i) 
        for(int j=0; j<N; ++j) dist_map[i][j] = 1e18;
    
    priority_queue<State, vector<State>, greater<State>> pq;
    dist_map[si][sj] = 0;
    pq.push({0, si, sj});
    
    while(!pq.empty()) {
        State top = pq.top(); pq.pop();
        int r = top.r, c = top.c;
        
        if(top.dist > dist_map[r][c]) continue;
        if(r == ti && c == tj) break;
        
        for(auto& e : adj[r][c]) {
            double w = (e.type == 0 ? h[e.w_r][e.w_c] : v[e.w_r][e.w_c]);
            if(dist_map[r][c] + w < dist_map[e.to_r][e.to_c]) {
                dist_map[e.to_r][e.to_c] = dist_map[r][c] + w;
                parent_node[e.to_r][e.to_c] = {r, c};
                pq.push({dist_map[e.to_r][e.to_c], e.to_r, e.to_c});
            }
        }
    }
    
    string path = "";
    int curr = ti, curc = tj;
    path_edges.clear();
    
    while(curr != si || curc != sj) {
        pair<int,int> p = parent_node[curr][curc];
        int pr = p.first;
        int pc = p.second;
        // Find the edge used
        for(auto& e : adj[pr][pc]) {
            if(e.to_r == curr && e.to_c == curc) {
                path += e.dir;
                path_edges.push_back(make_tuple(e.type, e.w_r, e.w_c));
                break;
            }
        }
        curr = pr; curc = pc;
    }
    reverse(path.begin(), path.end());
    // path_edges is reversed (destination to source), but order doesn't matter for updates
    return path;
}

int main() {
    init();
    
    int si, sj, ti, tj, b_k;
    // Learning rates
    double alpha = 0.25; // For edges actually traversed
    double beta = 0.015;  // For edges in the same row/column (structural correlation)
    
    for(int k=0; k<1000; ++k) {
        if(!(cin >> si >> sj >> ti >> tj)) break;
        
        vector<tuple<int,int,int>> path_edges;
        string s = get_path(si, sj, ti, tj, path_edges);
        cout << s << endl; // flush happens here with endl
        
        cin >> b_k;
        
        // Calculate estimated length with current weights
        double estimated = 0;
        for(auto& t : path_edges) {
            if(get<0>(t) == 0) estimated += h[get<1>(t)][get<2>(t)];
            else estimated += v[get<1>(t)][get<2>(t)];
        }
        
        int L = path_edges.size();
        if(L == 0) continue;
        
        double diff = b_k - estimated;
        double delta = diff / L; // Average error per edge
        
        // Update weights
        for(auto& t : path_edges) {
            int type = get<0>(t);
            int r = get<1>(t);
            int c = get<2>(t);
            
            if(type == 0) { // Horizontal edge
                // Update specific edge
                h[r][c] += alpha * delta;
                if(h[r][c] < 100.0) h[r][c] = 100.0;
                
                // Update other edges in the same row
                for(int j=0; j<N-1; ++j) {
                    if(j == c) continue;
                    h[r][j] += beta * delta;
                    if(h[r][j] < 100.0) h[r][j] = 100.0;
                }
            } else { // Vertical edge
                // Update specific edge
                v[r][c] += alpha * delta;
                if(v[r][c] < 100.0) v[r][c] = 100.0;
                
                // Update other edges in the same column
                for(int i=0; i<N-1; ++i) {
                    if(i == r) continue;
                    v[i][c] += beta * delta;
                    if(v[i][c] < 100.0) v[i][c] = 100.0;
                }
            }
        }
    }
    return 0;
}