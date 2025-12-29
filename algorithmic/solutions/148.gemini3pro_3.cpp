#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <bitset>
#include <ctime>

using namespace std;

// Problem Constants
const int MAX_GRID = 50;
const int MAX_TILES = 2500;
// Execution time limit safety margin (limit is usually 2.0s)
const double TIME_LIMIT = 1.90;

// Global Inputs
int si, sj;
int tile_map[MAX_GRID][MAX_GRID];
int points[MAX_GRID][MAX_GRID];
int num_tiles = 0;

// Structures for Path Reconstruction and Beam State
struct HistoryNode {
    int parent_idx; // Index in the previous level's history
    char move;      // Move taken ('U', 'D', 'L', 'R')
};

struct BeamState {
    int r, c;
    int score;
    int history_idx; // Index in the current level's history
    bitset<MAX_TILES> visited; // Track visited tiles
};

// History storage: all_history[depth][index]
vector<vector<HistoryNode>> all_history;

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    // Reading Input
    if (!(cin >> si >> sj)) return 0;

    for (int i = 0; i < MAX_GRID; ++i) {
        for (int j = 0; j < MAX_GRID; ++j) {
            cin >> tile_map[i][j];
            if (tile_map[i][j] >= num_tiles) num_tiles = tile_map[i][j] + 1;
        }
    }
    for (int i = 0; i < MAX_GRID; ++i) {
        for (int j = 0; j < MAX_GRID; ++j) {
            cin >> points[i][j];
        }
    }

    // Directions
    int dr[] = {-1, 1, 0, 0};
    int dc[] = {0, 0, -1, 1};
    char dchar[] = {'U', 'D', 'L', 'R'};

    clock_t start_time = clock();
    
    // Beam Search Parameters
    // We can handle a reasonably large beam width due to efficient bitset operations
    int beam_width = 2000; 
    
    vector<BeamState> current_beam;
    current_beam.reserve(beam_width * 4);
    
    // Initial State
    BeamState initial_state;
    initial_state.r = si;
    initial_state.c = sj;
    initial_state.score = points[si][sj];
    initial_state.history_idx = 0;
    initial_state.visited.reset();
    initial_state.visited.set(tile_map[si][sj]);
    
    current_beam.push_back(initial_state);
    
    // Initialize history with Start node
    all_history.reserve(MAX_TILES + 100);
    all_history.push_back({});
    all_history[0].push_back({-1, 'S'});

    // Track the best solution found so far
    int best_score = points[si][sj];
    pair<int, int> best_end_ref = {0, 0}; // {depth, index}

    int depth = 0;
    while (!current_beam.empty()) {
        // Time Check
        clock_t now = clock();
        double elapsed = double(now - start_time) / CLOCKS_PER_SEC;
        if (elapsed > TIME_LIMIT) break;
        
        // Adaptive Beam Width: reduce if running too slow to reach deep
        if (depth > 0 && depth % 50 == 0) {
            if (elapsed > 1.0) { 
                double projected = elapsed * (2500.0 / depth);
                if (projected > 1.85) {
                    beam_width = max(50, (int)(beam_width * 0.6));
                }
            }
        }
        
        vector<BeamState> next_candidates;
        next_candidates.reserve(current_beam.size() * 4);
        
        // Prepare history for next depth
        all_history.push_back({});
        all_history.back().reserve(current_beam.size() * 4);
        
        bool extended = false;

        for (const auto& state : current_beam) {
            for (int i = 0; i < 4; ++i) {
                int nr = state.r + dr[i];
                int nc = state.c + dc[i];
                
                // Boundary check
                if (nr >= 0 && nr < MAX_GRID && nc >= 0 && nc < MAX_GRID) {
                    int tid = tile_map[nr][nc];
                    // Constraint: Cannot step on visited tile
                    if (!state.visited.test(tid)) {
                        
                        BeamState next_state;
                        next_state.r = nr;
                        next_state.c = nc;
                        next_state.score = state.score + points[nr][nc];
                        next_state.visited = state.visited; // Efficient bitset copy
                        next_state.visited.set(tid);
                        
                        // Record in history
                        int h_idx = (int)all_history[depth + 1].size();
                        all_history[depth + 1].push_back({state.history_idx, dchar[i]});
                        next_state.history_idx = h_idx;
                        
                        next_candidates.push_back(next_state);
                        
                        // Update global best
                        if (next_state.score > best_score) {
                            best_score = next_state.score;
                            best_end_ref = {depth + 1, h_idx};
                        }
                        extended = true;
                    }
                }
            }
        }
        
        if (!extended) {
            break;
        }

        // Beam Pruning: keep top beam_width states
        if ((int)next_candidates.size() > beam_width) {
            // Partial sort to find top K
            nth_element(next_candidates.begin(), next_candidates.begin() + beam_width, next_candidates.end(),
                [](const BeamState& a, const BeamState& b) {
                    return a.score > b.score;
                });
            next_candidates.resize(beam_width);
        }
        
        current_beam = move(next_candidates);
        depth++;
    }
    
    // Path Reconstruction
    string path = "";
    int cur_depth = best_end_ref.first;
    int cur_idx = best_end_ref.second;
    
    while (cur_depth > 0) {
        HistoryNode node = all_history[cur_depth][cur_idx];
        path += node.move;
        cur_idx = node.parent_idx;
        cur_depth--;
    }
    
    reverse(path.begin(), path.end());
    cout << path << endl;

    return 0;
}