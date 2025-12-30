#include <iostream>
#include <vector>
#include <queue>
#include <tuple>
#include <algorithm>

using namespace std;

// Define directions and their characters
// U: (-1, 0), D: (1, 0), L: (0, -1), R: (0, 1)
const int dr[] = {-1, 1, 0, 0};
const int dc[] = {0, 0, -1, 1};
const char dchar[] = {'U', 'D', 'L', 'R'};

const int N = 20;
const int INF = 1e9;

// Check if coordinates are within the grid
bool isValid(int r, int c) {
    return r >= 0 && r < N && c >= 0 && c < N;
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n_in, m_in;
    if (!(cin >> n_in >> m_in)) return 0;
    
    int curr_r, curr_c;
    cin >> curr_r >> curr_c;
    
    vector<pair<int, int>> targets(m_in);
    for (int i = 0; i < m_in; ++i) {
        cin >> targets[i].first >> targets[i].second;
    }
    
    // We process targets one by one.
    // Since we never place blocks (Alter), the grid remains empty except for boundaries.
    // This allows us to simplify the Slide logic: slides always end at the grid boundaries.
    // We use BFS to find the shortest path in terms of actions (Move or Slide) for each target.
    
    for (int k = 0; k < m_in; ++k) {
        int tr = targets[k].first;
        int tc = targets[k].second;
        
        // If already at target, skip
        if (curr_r == tr && curr_c == tc) continue;
        
        // BFS Initialization
        // dist[r][c] stores min actions to reach (r,c)
        vector<vector<int>> dist(N, vector<int>(N, INF));
        
        // Parent info to reconstruct path
        struct Parent {
            int r, c;
            char type; // 'M' or 'S'
            char dir;  // 'U', 'D', 'L', 'R'
        };
        vector<vector<Parent>> parent(N, vector<Parent>(N, {-1, -1, ' ', ' '}));
        
        queue<pair<int, int>> q;
        
        dist[curr_r][curr_c] = 0;
        q.push({curr_r, curr_c});
        
        bool found = false;
        while(!q.empty()) {
            pair<int, int> u = q.front();
            q.pop();
            int r = u.first;
            int c = u.second;
            
            if (r == tr && c == tc) {
                found = true;
                break;
            }
            
            // Try Move actions (cost 1)
            for (int i = 0; i < 4; ++i) {
                int nr = r + dr[i];
                int nc = c + dc[i];
                
                if (isValid(nr, nc)) {
                    if (dist[nr][nc] == INF) {
                        dist[nr][nc] = dist[r][c] + 1;
                        parent[nr][nc] = {r, c, 'M', dchar[i]};
                        q.push({nr, nc});
                    }
                }
            }
            
            // Try Slide actions (cost 1)
            for (int i = 0; i < 4; ++i) {
                int nr = r;
                int nc = c;
                // Calculate slide destination assuming empty board (only boundaries stop the slide)
                // U: (0, c), D: (N-1, c), L: (r, 0), R: (r, N-1)
                if (dchar[i] == 'U') nr = 0;
                else if (dchar[i] == 'D') nr = N - 1;
                else if (dchar[i] == 'L') nc = 0;
                else if (dchar[i] == 'R') nc = N - 1;
                
                // Only consider if the slide actually moves us
                if (nr != r || nc != c) {
                    if (dist[nr][nc] == INF) {
                        dist[nr][nc] = dist[r][c] + 1;
                        parent[nr][nc] = {r, c, 'S', dchar[i]};
                        q.push({nr, nc});
                    }
                }
            }
        }
        
        // Reconstruct path
        vector<pair<char, char>> actions;
        int r = tr, c = tc;
        while (r != curr_r || c != curr_c) {
            Parent p = parent[r][c];
            actions.push_back({p.type, p.dir});
            r = p.r;
            c = p.c;
        }
        reverse(actions.begin(), actions.end());
        
        // Output actions
        for (auto p : actions) {
            cout << p.first << " " << p.second << "\n";
        }
        
        // Update current position
        curr_r = tr;
        curr_c = tc;
    }
    
    return 0;
}