#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <cmath>
#include <algorithm>

using namespace std;

// Grid size
const int N = 30;

// Estimated edge weights
// h[i][j]: horizontal edge between (i,j) and (i,j+1). Valid for i in 0..29, j in 0..28
// v[i][j]: vertical edge between (i,j) and (i+1,j). Valid for i in 0..28, j in 0..29
double h[N][N-1];
double v[N-1][N];

struct Point {
    int r, c;
    bool operator!=(const Point& other) const { return r != other.r || c != other.c; }
};

struct Node {
    int r, c;
    double dist;
    // Min-priority queue needs greater comparison
    bool operator>(const Node& other) const { return dist > other.dist; }
};

enum Dir { UP, DOWN, LEFT, RIGHT, NONE };

// Dijkstra Algorithm to find shortest path based on current weights
pair<string, vector<Point>> get_shortest_path(Point start, Point end_pt) {
    // Static arrays to avoid reallocation overhead given the strict time limit and repeated calls
    static double dist[N][N];
    static Point parent[N][N];
    static Dir parent_dir[N][N];
    
    // Initialize distances
    for(int i=0; i<N; ++i) {
        for(int j=0; j<N; ++j) {
            dist[i][j] = 1e18;
        }
    }
            
    dist[start.r][start.c] = 0;
    parent[start.r][start.c] = {-1, -1};
    parent_dir[start.r][start.c] = NONE;
    
    priority_queue<Node, vector<Node>, greater<Node>> pq;
    pq.push({start.r, start.c, 0});
    
    while(!pq.empty()) {
        Node top = pq.top();
        pq.pop();
        int r = top.r;
        int c = top.c;
        
        if(top.dist > dist[r][c]) continue;
        if(r == end_pt.r && c == end_pt.c) break;
        
        // Try all 4 directions
        // Down
        if(r+1 < N) {
            double w = v[r][c];
            if(dist[r+1][c] > dist[r][c] + w) {
                dist[r+1][c] = dist[r][c] + w;
                parent[r+1][c] = {r, c};
                parent_dir[r+1][c] = DOWN;
                pq.push({r+1, c, dist[r+1][c]});
            }
        }
        // Up
        if(r-1 >= 0) {
            double w = v[r-1][c];
            if(dist[r-1][c] > dist[r][c] + w) {
                dist[r-1][c] = dist[r][c] + w;
                parent[r-1][c] = {r, c};
                parent_dir[r-1][c] = UP;
                pq.push({r-1, c, dist[r-1][c]});
            }
        }
        // Right
        if(c+1 < N) {
            double w = h[r][c];
            if(dist[r][c+1] > dist[r][c] + w) {
                dist[r][c+1] = dist[r][c] + w;
                parent[r][c+1] = {r, c};
                parent_dir[r][c+1] = RIGHT;
                pq.push({r, c+1, dist[r][c+1]});
            }
        }
        // Left
        if(c-1 >= 0) {
            double w = h[r][c-1];
            if(dist[r][c-1] > dist[r][c] + w) {
                dist[r][c-1] = dist[r][c] + w;
                parent[r][c-1] = {r, c};
                parent_dir[r][c-1] = LEFT;
                pq.push({r, c-1, dist[r][c-1]});
            }
        }
    }
    
    // Reconstruct path
    string path = "";
    vector<Point> points;
    Point curr = end_pt;
    while(curr != start) {
        points.push_back(curr);
        Dir d = parent_dir[curr.r][curr.c];
        Point prev = parent[curr.r][curr.c];
        if(d == DOWN) path += 'D';
        else if(d == UP) path += 'U';
        else if(d == RIGHT) path += 'R';
        else if(d == LEFT) path += 'L';
        curr = prev;
    }
    points.push_back(start);
    reverse(path.begin(), path.end());
    return {path, points};
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    // Initialize weights to expected mean (5000)
    for(int i=0; i<N; ++i) for(int j=0; j<N-1; ++j) h[i][j] = 5000.0;
    for(int i=0; i<N-1; ++i) for(int j=0; j<N; ++j) v[i][j] = 5000.0;
    
    int Q = 1000;
    for(int k=0; k<Q; ++k) {
        int si, sj, ti, tj;
        if(!(cin >> si >> sj >> ti >> tj)) break;
        
        Point start = {si, sj};
        Point end_pt = {ti, tj};
        
        pair<string, vector<Point>> res = get_shortest_path(start, end_pt);
        cout << res.first << endl; // Flush is required
        
        int measured_int;
        cin >> measured_int;
        double measured = (double)measured_int;
        
        // Identify edges in the path and calculate predicted length
        double predicted = 0;
        // Store edges as {is_horizontal, {r, c}}
        vector<pair<bool, pair<int,int>>> edges; 
        
        Point curr = start;
        for(char c : res.first) {
            if(c == 'U') {
                predicted += v[curr.r-1][curr.c];
                edges.push_back({false, {curr.r-1, curr.c}});
                curr.r--;
            } else if(c == 'D') {
                predicted += v[curr.r][curr.c];
                edges.push_back({false, {curr.r, curr.c}});
                curr.r++;
            } else if(c == 'L') {
                predicted += h[curr.r][curr.c-1];
                edges.push_back({true, {curr.r, curr.c-1}});
                curr.c--;
            } else if(c == 'R') {
                predicted += h[curr.r][curr.c];
                edges.push_back({true, {curr.r, curr.c}});
                curr.c++;
            }
        }
        
        int len = edges.size();
        if(len == 0) continue;
        
        double diff = measured - predicted;
        double unit_diff = diff / len;
        
        // Learning parameters
        double lr = 0.25; 
        double neighbor_factor = 0.15;
        double decay = 0.7;
        
        // Update weights
        for(auto& edge : edges) {
            bool is_h = edge.first;
            int r = edge.second.first;
            int c = edge.second.second;
            
            if(is_h) {
                // Update specific edge
                h[r][c] += lr * unit_diff;
                h[r][c] = max(1000.0, min(9000.0, h[r][c]));
                
                // Update neighbors (smoothing in the same row)
                double d = unit_diff * neighbor_factor;
                // Left neighbors
                double cd = d;
                for(int dc = 1; c - dc >= 0; ++dc) {
                    cd *= decay;
                    if(abs(cd) < 1e-3) break;
                    h[r][c-dc] += cd;
                    h[r][c-dc] = max(1000.0, min(9000.0, h[r][c-dc]));
                }
                // Right neighbors
                cd = d;
                for(int dc = 1; c + dc < N-1; ++dc) {
                    cd *= decay;
                    if(abs(cd) < 1e-3) break;
                    h[r][c+dc] += cd;
                    h[r][c+dc] = max(1000.0, min(9000.0, h[r][c+dc]));
                }
            } else {
                // Update specific edge
                v[r][c] += lr * unit_diff;
                v[r][c] = max(1000.0, min(9000.0, v[r][c]));
                
                // Update neighbors (smoothing in the same column)
                double d = unit_diff * neighbor_factor;
                // Up neighbors
                double cd = d;
                for(int dr = 1; r - dr >= 0; ++dr) {
                    cd *= decay;
                    if(abs(cd) < 1e-3) break;
                    v[r-dr][c] += cd;
                    v[r-dr][c] = max(1000.0, min(9000.0, v[r-dr][c]));
                }
                // Down neighbors
                cd = d;
                for(int dr = 1; r + dr < N-1; ++dr) {
                    cd *= decay;
                    if(abs(cd) < 1e-3) break;
                    v[r+dr][c] += cd;
                    v[r+dr][c] = max(1000.0, min(9000.0, v[r+dr][c]));
                }
            }
        }
    }
    return 0;
}