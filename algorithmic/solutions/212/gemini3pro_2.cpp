#include <iostream>
#include <vector>
#include <queue>
#include <tuple>
#include <algorithm>

using namespace std;

// Represents the state in the Dijkstra search
struct State {
    int l, r;       // Current boundaries of the contiguous visited block of rows [l, r]
    int at_r;       // 0 if currently at row l, 1 if at row r
    int side;       // 0 if currently at Left (column L), 1 if at Right (column R)
    int idxQ;       // How many elements of sequence q have been satisfied
    int cost;       // Total steps taken
    int cL, cR;     // Number of tracks used in Left and Right corridors respectively

    bool operator>(const State& other) const {
        return cost > other.cost;
    }
};

// To reconstruct the path
struct Prev {
    int l, r, at_r, side, idxQ;
};

// Information about the move to reconstruct coordinates
struct MoveInfo {
    int type;   // 1: Adjacent move, 2: Jump via corridor
    int track;  // Track index used if type is Jump
};

int n, m, L, R, Sx, Sy, Lq, s;
vector<int> q;
int pos_in_q[45]; // pos_in_q[row] gives index in q if row is in q, else -1

// DP/Dijkstra tables
// Dimensions: [l][r][at_r][side][idxQ]
// l, r: 1..40
// at_r: 0..1
// side: 0..1
// idxQ: 0..Lq
int dist[42][42][2][2][42];
Prev parent[42][42][2][2][42];
MoveInfo moveMeta[42][42][2][2][42];

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> n >> m >> L >> R >> Sx >> Sy >> Lq >> s)) return 0;
    
    q.resize(Lq);
    for(int i = 0; i <= n; ++i) pos_in_q[i] = -1;
    for(int i = 0; i < Lq; ++i) {
        cin >> q[i];
        pos_in_q[q[i]] = i;
    }

    // Initialize distances
    for(int i = 0; i <= n; ++i)
        for(int j = 0; j <= n; ++j)
            for(int k = 0; k < 2; ++k)
                for(int u = 0; u < 2; ++u)
                    for(int v = 0; v <= Lq; ++v) {
                        dist[i][j][k][u][v] = 1e9;
                    }

    priority_queue<State, vector<State>, greater<State>> pq;

    // Initial state processing
    int init_idxQ = 0;
    if(pos_in_q[Sx] != -1) {
        if(pos_in_q[Sx] == 0) init_idxQ = 1;
        else {
            cout << "NO" << endl;
            return 0;
        }
    }

    // Starting at (Sx, Sy=L). Immediately traverse row Sx from L to R.
    // Ends at (Sx, R).
    // State: l=Sx, r=Sx, at_r=1 (bottom of block), side=1 (Right)
    int init_cost = R - L + 1;
    dist[Sx][Sx][1][1][init_idxQ] = init_cost;
    // Store init meta as 0
    moveMeta[Sx][Sx][1][1][init_idxQ] = {0, 0};
    
    pq.push({Sx, Sx, 1, 1, init_idxQ, init_cost, 0, 0});

    int final_l = -1, final_r = -1, final_at = -1, final_side = -1;
    int min_total = 1e9;

    while(!pq.empty()) {
        State cur = pq.top();
        pq.pop();

        if(cur.cost > dist[cur.l][cur.r][cur.at_r][cur.side][cur.idxQ]) continue;

        // Check if all rows visited and q satisfied
        if(cur.l == 1 && cur.r == n && cur.idxQ == Lq) {
            if(cur.cost < min_total) {
                min_total = cur.cost;
                final_l = cur.l; final_r = cur.r;
                final_at = cur.at_r; final_side = cur.side;
            }
            break; // Dijkstra guarantees first found is shortest
        }

        int curr_row = (cur.at_r == 0) ? cur.l : cur.r;

        // Try expanding upwards to l-1
        if(cur.l > 1) {
            int next_row = cur.l - 1;
            int n_idxQ = cur.idxQ;
            bool ok = true;
            if(pos_in_q[next_row] != -1) {
                if(pos_in_q[next_row] == cur.idxQ) n_idxQ++;
                else ok = false;
            }

            if(ok) {
                int added_cost = 0;
                int new_cL = cur.cL;
                int new_cR = cur.cR;
                int type = 0; 
                int track = 0;

                // Move from curr_row (side cur.side) to next_row (entry at cur.side)
                if(curr_row == cur.l) {
                    // Adjacent: l to l-1
                    added_cost = 1; 
                    type = 1;
                } else {
                    // Jump from r to l-1
                    type = 2;
                    int dist_v = cur.r - next_row;
                    if(cur.side == 0) { // Left corridor
                        if(cur.cL + 1 < L) {
                            new_cL++;
                            track = new_cL;
                            added_cost = dist_v + 2 * track;
                        } else ok = false;
                    } else { // Right corridor
                        if(cur.cR + 1 <= m - R) {
                            new_cR++;
                            track = new_cR;
                            added_cost = dist_v + 2 * track;
                        } else ok = false;
                    }
                }

                if(ok) {
                    added_cost += (R - L + 1); // Cost to traverse the row
                    int new_cost = cur.cost + added_cost;
                    // Target state: new range [l-1, r], at l-1 (top, at_r=0), side flipped
                    if(new_cost < dist[next_row][cur.r][0][1 - cur.side][n_idxQ]) {
                        dist[next_row][cur.r][0][1 - cur.side][n_idxQ] = new_cost;
                        parent[next_row][cur.r][0][1 - cur.side][n_idxQ] = {cur.l, cur.r, cur.at_r, cur.side, cur.idxQ};
                        moveMeta[next_row][cur.r][0][1 - cur.side][n_idxQ] = {type, track};
                        pq.push({next_row, cur.r, 0, 1 - cur.side, n_idxQ, new_cost, new_cL, new_cR});
                    }
                }
            }
        }

        // Try expanding downwards to r+1
        if(cur.r < n) {
            int next_row = cur.r + 1;
            int n_idxQ = cur.idxQ;
            bool ok = true;
            if(pos_in_q[next_row] != -1) {
                if(pos_in_q[next_row] == cur.idxQ) n_idxQ++;
                else ok = false;
            }

            if(ok) {
                int added_cost = 0;
                int new_cL = cur.cL;
                int new_cR = cur.cR;
                int type = 0; 
                int track = 0;

                if(curr_row == cur.r) {
                    // Adjacent: r to r+1
                    added_cost = 1;
                    type = 1;
                } else {
                    // Jump from l to r+1
                    type = 2;
                    int dist_v = next_row - cur.l;
                    if(cur.side == 0) {
                        if(cur.cL + 1 < L) {
                            new_cL++;
                            track = new_cL;
                            added_cost = dist_v + 2 * track;
                        } else ok = false;
                    } else {
                        if(cur.cR + 1 <= m - R) {
                            new_cR++;
                            track = new_cR;
                            added_cost = dist_v + 2 * track;
                        } else ok = false;
                    }
                }

                if(ok) {
                    added_cost += (R - L + 1);
                    int new_cost = cur.cost + added_cost;
                    // Target state: new range [l, r+1], at r+1 (bottom, at_r=1), side flipped
                    if(new_cost < dist[cur.l][next_row][1][1 - cur.side][n_idxQ]) {
                        dist[cur.l][next_row][1][1 - cur.side][n_idxQ] = new_cost;
                        parent[cur.l][next_row][1][1 - cur.side][n_idxQ] = {cur.l, cur.r, cur.at_r, cur.side, cur.idxQ};
                        moveMeta[cur.l][next_row][1][1 - cur.side][n_idxQ] = {type, track};
                        pq.push({cur.l, next_row, 1, 1 - cur.side, n_idxQ, new_cost, new_cL, new_cR});
                    }
                }
            }
        }
    }

    if(min_total == 1e9) {
        cout << "NO" << endl;
    } else {
        cout << "YES" << endl;
        cout << min_total << endl;
        
        // Reconstruct path
        vector<tuple<int, int, int, int>> steps; // row, entry_side, type, track
        int cl = final_l, cr = final_r, cat = final_at, cside = final_side, ci = Lq;
        
        while(true) {
            // Check base case
            if(cl == Sx && cr == Sx && cat == 1 && cside == 1 && ci == init_idxQ) break;
            
            Prev p = parent[cl][cr][cat][cside][ci];
            MoveInfo m = moveMeta[cl][cr][cat][cside][ci];
            int row = (cat == 0) ? cl : cr;
            // The side we entered this row from is the side we were at in previous state
            int entry_side = p.side; 
            steps.push_back({row, entry_side, m.type, m.track});
            
            cl = p.l; cr = p.r; cat = p.at_r; cside = p.side; ci = p.idxQ;
        }
        
        reverse(steps.begin(), steps.end());
        
        // Output coordinates
        // Initial traversal of Sx
        vector<pair<int,int>> path;
        for(int c = L; c <= R; ++c) path.push_back({Sx, c});
        
        int cur_r = Sx, cur_c = R; 
        
        for(auto step : steps) {
            int next_row = get<0>(step);
            int entry_s = get<1>(step);
            int type = get<2>(step);
            int track = get<3>(step);
            
            int entry_col = (entry_s == 0) ? L : R;
            
            if(type == 1) {
                // Adjacent
                path.push_back({next_row, entry_col});
            } else {
                // Jump via corridor
                int corridor_col;
                if(entry_s == 0) corridor_col = L - track;
                else corridor_col = R + track;
                
                // step out
                int step_dir = (corridor_col > cur_c) ? 1 : -1;
                for(int c = cur_c + step_dir; c != corridor_col + step_dir; c += step_dir) {
                    path.push_back({cur_r, c});
                }
                // vertical
                step_dir = (next_row > cur_r) ? 1 : -1;
                for(int r = cur_r + step_dir; r != next_row + step_dir; r += step_dir) {
                    path.push_back({r, corridor_col});
                }
                // step in
                step_dir = (entry_col > corridor_col) ? 1 : -1;
                for(int c = corridor_col + step_dir; c != entry_col + step_dir; c += step_dir) {
                    path.push_back({next_row, c});
                }
            }
            
            // Traverse the row
            int end_col = (entry_s == 0) ? R : L;
            int trav_dir = (end_col > entry_col) ? 1 : -1;
            for(int c = entry_col + trav_dir; c != end_col + trav_dir; c += trav_dir) {
                path.push_back({next_row, c});
            }
            
            cur_r = next_row;
            cur_c = end_col;
        }
        
        for(auto p : path) {
            cout << p.first << " " << p.second << "\n";
        }
    }

    return 0;
}