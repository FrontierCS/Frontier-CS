#include <iostream>
#include <vector>
#include <queue>
#include <tuple>
#include <algorithm>

using namespace std;

const int N = 20;
const int INF = 1e9;

struct Point {
    int r, c;
};

// Directions: U, D, L, R
// Corresponds to indices 0, 1, 2, 3
int dr[] = {-1, 1, 0, 0};
int dc[] = {0, 0, -1, 1};
char dchar[] = {'U', 'D', 'L', 'R'};

struct Node {
    int cost;
    int r, c;
    bool operator>(const Node& other) const {
        return cost > other.cost;
    }
};

struct Parent {
    int r, c;
    char action; // 'M' or 'S'
    char dir;    // 'U', 'D', 'L', 'R'
};

// Function to find where a slide stops on an empty grid.
// Since we don't place blocks, the grid remains empty inside N x N,
// so slides only stop at the boundaries.
Point get_slide_stop(int r, int c, int d) {
    int nr = r + dr[d];
    int nc = c + dc[d];
    // Keep moving while inside grid
    while (nr >= 0 && nr < N && nc >= 0 && nc < N) {
        nr += dr[d];
        nc += dc[d];
    }
    // Step back to last valid position (just before the "block" outside the grid)
    return {nr - dr[d], nc - dc[d]};
}

int main() {
    // Speed up I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n_in, m_in;
    if (!(cin >> n_in >> m_in)) return 0;
    
    // We store the sequence of coordinates.
    // The first one is the start position, the rest are targets.
    vector<Point> targets(m_in);
    for (int i = 0; i < m_in; ++i) {
        cin >> targets[i].r >> targets[i].c;
    }
    
    // Current position starts at i0, j0
    Point curr = targets[0];
    
    // Loop through subsequent targets
    for (int k = 1; k < m_in; ++k) {
        Point target = targets[k];
        
        // Use Dijkstra (or BFS) to find shortest path from curr to target.
        // The graph nodes are grid cells (r, c).
        // Edges: 
        // 1. Move to adjacent cell: Cost 1.
        // 2. Slide to boundary: Cost 1.
        // We assume the grid is empty of internal blocks, which holds true since we never 'Alter'.
        
        vector<vector<int>> dist(N, vector<int>(N, INF));
        vector<vector<Parent>> parent(N, vector<Parent>(N, {-1, -1, ' ', ' '}));
        
        priority_queue<Node, vector<Node>, greater<Node>> pq;
        
        dist[curr.r][curr.c] = 0;
        pq.push({0, curr.r, curr.c});
        
        while (!pq.empty()) {
            Node top = pq.top();
            pq.pop();
            
            int r = top.r;
            int c = top.c;
            int cost = top.cost;
            
            if (cost > dist[r][c]) continue;
            if (r == target.r && c == target.c) break;
            
            // Try Moves (M)
            for (int d = 0; d < 4; ++d) {
                int nr = r + dr[d];
                int nc = c + dc[d];
                
                if (nr >= 0 && nr < N && nc >= 0 && nc < N) {
                    int new_cost = cost + 1;
                    if (new_cost < dist[nr][nc]) {
                        dist[nr][nc] = new_cost;
                        parent[nr][nc] = {r, c, 'M', dchar[d]};
                        pq.push({new_cost, nr, nc});
                    }
                }
            }
            
            // Try Slides (S)
            for (int d = 0; d < 4; ++d) {
                Point stop = get_slide_stop(r, c, d);
                
                // If sliding in direction d doesn't move us (e.g. at boundary), skip
                if (stop.r == r && stop.c == c) continue;

                int new_cost = cost + 1;
                if (new_cost < dist[stop.r][stop.c]) {
                    dist[stop.r][stop.c] = new_cost;
                    parent[stop.r][stop.c] = {r, c, 'S', dchar[d]};
                    pq.push({new_cost, stop.r, stop.c});
                }
            }
        }
        
        // Reconstruct path from target back to curr
        vector<pair<char, char>> actions;
        int r = target.r;
        int c = target.c;
        while (r != curr.r || c != curr.c) {
            Parent p = parent[r][c];
            actions.push_back({p.action, p.dir});
            r = p.r;
            c = p.c;
        }
        reverse(actions.begin(), actions.end());
        
        // Output actions for this segment
        for (auto p : actions) {
            cout << p.first << " " << p.second << "\n";
        }
        
        // Update current position
        curr = target;
    }
    
    return 0;
}