#include <iostream>
#include <vector>
#include <string>
#include <algorithm>
#include <map>
#include <set>

using namespace std;

// Represents a possible state of the user: position (r, c) and direction
struct State {
    int r, c, dir;
    // Comparison for sorting/sets
    bool operator<(const State& other) const {
        if (r != other.r) return r < other.r;
        if (c != other.c) return c < other.c;
        return dir < other.dir;
    }
    bool operator==(const State& other) const {
        return r == other.r && c == other.c && dir == other.dir;
    }
};

int R, C;
vector<string> grid;
// Directions: 0: North, 1: East, 2: South, 3: West
int dr[] = {-1, 0, 1, 0};
int dc[] = {0, 1, 0, -1};

// Check if a cell is within bounds and is an open square
bool isValid(int r, int c) {
    return r >= 0 && r < R && c >= 0 && c < C && grid[r][c] == '.';
}

// Calculate distance to the nearest wall in the given direction
int get_dist(int r, int c, int dir) {
    int d = 0;
    while (true) {
        int nr = r + dr[dir];
        int nc = c + dc[dir];
        if (isValid(nr, nc)) {
            d++;
            r = nr;
            c = nc;
        } else {
            break;
        }
    }
    return d;
}

// Apply a move to a state and return the resulting state
State apply_move(State s, string move) {
    if (move == "left") {
        return {s.r, s.c, (s.dir + 3) % 4};
    } else if (move == "right") {
        return {s.r, s.c, (s.dir + 1) % 4};
    } else if (move == "step") {
        return {s.r + dr[s.dir], s.c + dc[s.dir], s.dir};
    }
    return s;
}

// Convert state to a unique integer index for array mapping
int stateToIndex(State s) {
    return (s.r * C + s.c) * 4 + s.dir;
}

// Stores equivalence class ID for each state to detect impossible scenarios
vector<int> equivClass;

// Precompute equivalence classes to identify indistinguishable states
void computeEquivalence() {
    int totalStates = R * C * 4;
    equivClass.assign(totalStates, -1);
    
    // Initial partition based on the immediate observation (distance to wall)
    for (int r = 0; r < R; ++r) {
        for (int c = 0; c < C; ++c) {
            if (grid[r][c] == '#') continue;
            for (int d = 0; d < 4; ++d) {
                equivClass[stateToIndex({r, c, d})] = get_dist(r, c, d);
            }
        }
    }
    
    // Iteratively refine classes based on transitions
    while (true) {
        // Signatures store { {current_class, left_class, right_class, step_class}, original_index }
        vector<pair<vector<int>, int>> signatures;
        signatures.reserve(totalStates);
        
        for (int r = 0; r < R; ++r) {
            for (int c = 0; c < C; ++c) {
                if (grid[r][c] == '#') continue;
                for (int d = 0; d < 4; ++d) {
                    State s = {r, c, d};
                    int idx = stateToIndex(s);
                    
                    int dist = get_dist(r, c, d);
                    int clsL = equivClass[stateToIndex(apply_move(s, "left"))];
                    int clsR = equivClass[stateToIndex(apply_move(s, "right"))];
                    int clsS = -1;
                    if (dist > 0) {
                        // Step is only a valid transition if distance > 0
                        clsS = equivClass[stateToIndex(apply_move(s, "step"))];
                    }
                    
                    signatures.push_back({{equivClass[idx], clsL, clsR, clsS}, idx});
                }
            }
        }
        
        sort(signatures.begin(), signatures.end());
        
        vector<int> newClass(totalStates, -1);
        int currentID = 0;
        bool changed = false;
        
        for (size_t i = 0; i < signatures.size(); ++i) {
            if (i > 0 && signatures[i].first != signatures[i-1].first) {
                currentID++;
            }
            int idx = signatures[i].second;
            newClass[idx] = currentID;
            if (newClass[idx] != equivClass[idx]) changed = true;
        }
        
        equivClass = newClass;
        if (!changed) break;
    }
}

int main() {
    // Fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> R >> C)) return 0;
    grid.resize(R);
    vector<State> candidates;
    for (int i = 0; i < R; ++i) {
        cin >> grid[i];
        for (int j = 0; j < C; ++j) {
            if (grid[i][j] == '.') {
                for (int d = 0; d < 4; ++d) {
                    candidates.push_back({i, j, d});
                }
            }
        }
    }

    computeEquivalence();

    while (true) {
        int d;
        cin >> d;
        if (d == -1) break; 

        // 1. Filter candidates based on the current observation d
        vector<State> next_candidates;
        next_candidates.reserve(candidates.size());
        for (const auto& s : candidates) {
            if (get_dist(s.r, s.c, s.dir) == d) {
                next_candidates.push_back(s);
            }
        }
        candidates = next_candidates;

        // 2. Check if the user's location is uniquely determined
        set<pair<int, int>> locs;
        for (const auto& s : candidates) locs.insert({s.r, s.c});
        
        if (locs.size() == 1) {
            cout << "yes " << locs.begin()->first + 1 << " " << locs.begin()->second + 1 << endl;
            return 0;
        }
        
        // 3. Check if it's impossible to uniquely determine position
        // If all candidates are indistinguishable (same equivalence class) but imply different locations
        if (!candidates.empty()) {
            int firstClass = equivClass[stateToIndex(candidates[0])];
            bool allSame = true;
            for (const auto& s : candidates) {
                if (equivClass[stateToIndex(s)] != firstClass) {
                    allSame = false;
                    break;
                }
            }
            if (allSame && locs.size() > 1) {
                cout << "no" << endl;
                return 0;
            }
        }

        // 4. Determine the best move to minimize expected future rounds
        string bestMove = "";
        long long minMaxSplit = -1;
        long long minSumSq = -1;
        
        vector<string> moves = {"left", "right"};
        // "step" is valid only if there is space in front (d > 0)
        // Since we filtered candidates by d, if d > 0, all candidates can step.
        if (d > 0) moves.push_back("step");
        
        // Greedy Strategy: Pick move that minimizes the maximum size of resultant partitions (Minimax)
        // Tie-breaker: Minimize sum of squares of partition sizes (Entropy approximation)
        // Second Tie-breaker: Prefer "step" to explore, then consistent turns.
        for (const string& m : moves) {
            map<int, int> counts;
            for (const auto& s : candidates) {
                State nextS = apply_move(s, m);
                int obs = get_dist(nextS.r, nextS.c, nextS.dir);
                counts[obs]++;
            }
            
            long long maxSplit = 0;
            long long sumSq = 0;
            for (auto const& [val, count] : counts) {
                if (count > maxSplit) maxSplit = count;
                sumSq += (long long)count * count;
            }
            
            bool better = false;
            if (bestMove == "") {
                better = true;
            } else {
                if (maxSplit < minMaxSplit) {
                    better = true;
                } else if (maxSplit == minMaxSplit) {
                    if (sumSq < minSumSq) {
                        better = true;
                    } else if (sumSq == minSumSq) {
                        // Prefer stepping if metrics are identical (avoids getting stuck in rotation loops)
                        if (m == "step") better = true;
                        else if (m == "right" && bestMove == "left") better = true;
                    }
                }
            }
            
            if (better) {
                bestMove = m;
                minMaxSplit = maxSplit;
                minSumSq = sumSq;
            }
        }
        
        cout << bestMove << endl;
        
        // 5. Update candidates to reflect the move taken (state before next observation)
        vector<State> updated_candidates;
        updated_candidates.reserve(candidates.size());
        for (const auto& s : candidates) {
            updated_candidates.push_back(apply_move(s, bestMove));
        }
        candidates = updated_candidates;
    }
    return 0;
}