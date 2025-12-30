#include <iostream>
#include <vector>
#include <queue>
#include <tuple>
#include <algorithm>

using namespace std;

// Direction constants: Up, Down, Left, Right
const int DR[] = {-1, 1, 0, 0};
const int DC[] = {0, 0, -1, 1};
const char DCHAR[] = {'U', 'D', 'L', 'R'};

// State structure for Dijkstra
struct State {
    int r, c;
    int cost;
    
    // Min-priority queue needs greater operator
    bool operator>(const State& other) const {
        return cost > other.cost;
    }
};

// Structure to track path for reconstruction
struct ParentInfo {
    int pr, pc;   // Previous row, col
    char act;     // Action taken ('M' or 'S')
    int d;        // Direction index
};

// Global variables for grid dimensions and targets
int N, M;
vector<pair<int, int>> targets;

/**
 * Calculates the destination coordinates when sliding from (r, c) in direction dir.
 * Since we adopt a strategy of not placing blocks, the grid interior is always empty.
 * Slides stop only at the boundaries of the N x N grid.
 */
pair<int, int> get_slide_dest(int r, int c, int dir) {
    if (dir == 0) return {0, c};       // Slide Up -> Stop at row 0
    if (dir == 1) return {N - 1, c};   // Slide Down -> Stop at row N-1
    if (dir == 2) return {r, 0};       // Slide Left -> Stop at col 0
    if (dir == 3) return {r, N - 1};   // Slide Right -> Stop at col N-1
    return {r, c};
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    // Read problem parameters
    if (!(cin >> N >> M)) return 0;

    targets.resize(M);
    for (int i = 0; i < M; ++i) {
        cin >> targets[i].first >> targets[i].second;
    }

    // Start simulation from the initial position
    int curr_r = targets[0].first;
    int curr_c = targets[0].second;

    // Process each target sequentially
    for (int k = 1; k < M; ++k) {
        int target_r = targets[k].first;
        int target_c = targets[k].second;

        // Use Dijkstra's algorithm to find the shortest path of Moves and Slides
        // considering the grid is empty.
        vector<vector<int>> dist(N, vector<int>(N, 1e9));
        vector<vector<ParentInfo>> parent(N, vector<ParentInfo>(N, {-1, -1, ' ', -1}));
        
        priority_queue<State, vector<State>, greater<State>> pq;

        dist[curr_r][curr_c] = 0;
        pq.push({curr_r, curr_c, 0});

        while (!pq.empty()) {
            State top = pq.top();
            pq.pop();
            
            int r = top.r;
            int c = top.c;
            int cost = top.cost;

            // If we found a shorter path to this node already, skip
            if (cost > dist[r][c]) continue;
            
            // If we reached the target, we can stop Dijkstra for this leg
            if (r == target_r && c == target_c) break;

            // 1. Try 'Move' actions (1 step in any direction)
            for (int d = 0; d < 4; ++d) {
                int nr = r + DR[d];
                int nc = c + DC[d];

                // Check bounds
                if (nr >= 0 && nr < N && nc >= 0 && nc < N) {
                    if (dist[nr][nc] > cost + 1) {
                        dist[nr][nc] = cost + 1;
                        parent[nr][nc] = {r, c, 'M', d};
                        pq.push({nr, nc, cost + 1});
                    }
                }
            }

            // 2. Try 'Slide' actions (slide until boundary)
            for (int d = 0; d < 4; ++d) {
                pair<int, int> dest = get_slide_dest(r, c, d);
                int nr = dest.first;
                int nc = dest.second;

                // If sliding doesn't change position, it's not a useful move
                if (nr == r && nc == c) continue;

                if (dist[nr][nc] > cost + 1) {
                    dist[nr][nc] = cost + 1;
                    parent[nr][nc] = {r, c, 'S', d};
                    pq.push({nr, nc, cost + 1});
                }
            }
        }

        // Reconstruct the path from target back to start of this leg
        vector<pair<char, char>> actions;
        int r = target_r;
        int c = target_c;

        while (r != curr_r || c != curr_c) {
            ParentInfo p = parent[r][c];
            actions.push_back({p.act, DCHAR[p.d]});
            r = p.pr;
            c = p.pc;
        }
        reverse(actions.begin(), actions.end());

        // Output the actions
        for (const auto& action : actions) {
            cout << action.first << " " << action.second << "\n";
        }

        // Update current position to the target we just reached
        curr_r = target_r;
        curr_c = target_c;
    }

    return 0;
}