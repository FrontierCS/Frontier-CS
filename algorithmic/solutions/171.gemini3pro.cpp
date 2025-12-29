#include <iostream>
#include <vector>
#include <queue>
#include <tuple>
#include <algorithm>

using namespace std;

// Constants defined in the problem
const int N = 20;
const int M = 40;

// Directions arrays
// 0: Up, 1: Down, 2: Left, 3: Right
const int DR[] = {-1, 1, 0, 0}; 
const int DC[] = {0, 0, -1, 1};
const char DIRS[] = {'U', 'D', 'L', 'R'};

struct Point {
    int r, c;
    bool operator==(const Point& other) const {
        return r == other.r && c == other.c;
    }
};

struct Action {
    char type; // 'M' or 'S'
    char dir;
};

bool isValid(int r, int c) {
    return r >= 0 && r < N && c >= 0 && c < N;
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n_in, m_in;
    if (!(cin >> n_in >> m_in)) return 0;
    
    vector<Point> targets(M);
    for (int i = 0; i < M; ++i) {
        cin >> targets[i].r >> targets[i].c;
    }

    Point curr = targets[0];

    // Iterate through each target to visit sequentially
    // We start at targets[0] and need to visit targets[1], then targets[2], ...
    for (int k = 1; k < M; ++k) {
        Point goal = targets[k];

        // BFS to find the shortest path in terms of turns.
        // The grid is assumed to be empty (no internal blocks), 
        // so we can use Moves and Slides against the walls.
        
        // dist[r][c] stores min steps to reach (r,c)
        vector<vector<int>> dist(N, vector<int>(N, -1));
        // parent stores reconstruction info: {prev_r, prev_c, action_type, direction_index}
        vector<vector<tuple<int, int, char, int>>> parent(N, vector<tuple<int, int, char, int>>(N, make_tuple(-1, -1, ' ', -1)));

        queue<Point> q;
        
        dist[curr.r][curr.c] = 0;
        q.push(curr);

        while (!q.empty()) {
            Point u = q.front();
            q.pop();

            if (u == goal) {
                break;
            }

            // 1. Try Move actions
            for (int d = 0; d < 4; ++d) {
                int nr = u.r + DR[d];
                int nc = u.c + DC[d];

                if (isValid(nr, nc)) {
                    if (dist[nr][nc] == -1) {
                        dist[nr][nc] = dist[u.r][u.c] + 1;
                        parent[nr][nc] = make_tuple(u.r, u.c, 'M', d);
                        q.push({nr, nc});
                    }
                }
            }

            // 2. Try Slide actions
            // In an empty grid, slide goes until the grid boundary.
            for (int d = 0; d < 4; ++d) {
                int nr = u.r;
                int nc = u.c;

                // Determine stopping position based on direction
                if (d == 0) nr = 0;          // Up -> Row 0
                else if (d == 1) nr = N - 1; // Down -> Row N-1
                else if (d == 2) nc = 0;     // Left -> Col 0
                else if (d == 3) nc = N - 1; // Right -> Col N-1

                // Check if the slide actually moves us to a valid new position
                if (isValid(nr, nc)) { 
                    if (dist[nr][nc] == -1) {
                        dist[nr][nc] = dist[u.r][u.c] + 1;
                        parent[nr][nc] = make_tuple(u.r, u.c, 'S', d);
                        q.push({nr, nc});
                    }
                }
            }
        }

        // Reconstruct path
        vector<Action> path;
        Point p = goal;
        while (!(p == curr)) {
            tuple<int, int, char, int> info = parent[p.r][p.c];
            int pr = get<0>(info);
            int pc = get<1>(info);
            char type = get<2>(info);
            int dir_idx = get<3>(info);

            path.push_back({type, DIRS[dir_idx]});
            p = {pr, pc};
        }
        reverse(path.begin(), path.end());

        // Output the path
        for (const auto& act : path) {
            cout << act.type << " " << act.dir << "\n";
        }

        // Update current position
        curr = goal;
    }

    return 0;
}