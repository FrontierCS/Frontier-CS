#include <iostream>
#include <vector>
#include <queue>
#include <tuple>
#include <algorithm>
#include <map>

using namespace std;

struct State {
    int l, r, pos, q_idx, side;
    
    bool operator<(const State& other) const {
        return tie(l, r, pos, q_idx, side) < tie(other.l, other.r, other.pos, other.q_idx, other.side);
    }
    bool operator==(const State& other) const {
        return tie(l, r, pos, q_idx, side) == tie(other.l, other.r, other.pos, other.q_idx, other.side);
    }
};

struct Node {
    int cost;
    int dL, dR;
    State s;
    
    bool operator>(const Node& other) const {
        return cost > other.cost;
    }
};

struct Prev {
    State p_s;
    int move_type; // 0: init, 1: adj, 2: jump
};

int n, m, L, R, Sx, Sy, Lq;
double S_score;
vector<int> Q;
int pos_in_q[45];

int dist[42][42][2][42][2];
pair<int, int> depths[42][42][2][42][2];
Prev parent[42][42][2][42][2];
bool visited[42][42][2][42][2];

// Constants for side
const int SIDE_R = 0;
const int SIDE_L = 1;
// Constants for pos
const int POS_L = 0;
const int POS_R = 1;

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    if (!(cin >> n >> m >> L >> R >> Sx >> Sy >> Lq >> S_score)) return 0;
    
    Q.resize(Lq);
    fill(pos_in_q, pos_in_q + 45, -1);
    for (int i = 0; i < Lq; ++i) {
        cin >> Q[i];
        pos_in_q[Q[i]] = i;
    }

    // Init dist
    for(int i=0; i<42; ++i)
        for(int j=0; j<42; ++j)
            for(int k=0; k<2; ++k)
                for(int l=0; l<42; ++l)
                    for(int s=0; s<2; ++s) {
                        dist[i][j][k][l][s] = 1e9;
                        visited[i][j][k][l][s] = false;
                    }

    priority_queue<Node, vector<Node>, greater<Node>> pq;

    // Initial state
    int start_q = 0;
    if (pos_in_q[Sx] != -1) {
        if (pos_in_q[Sx] == 0) start_q = 1;
        else {
            cout << "NO" << endl;
            return 0;
        }
    }
    
    State startState = {Sx, Sx, POS_L, start_q, SIDE_R}; 
    
    dist[Sx][Sx][POS_L][start_q][SIDE_R] = 0;
    depths[Sx][Sx][POS_L][start_q][SIDE_R] = {0, 0};
    pq.push({0, 0, 0, startState});
    parent[Sx][Sx][POS_L][start_q][SIDE_R] = {{0,0,0,0,0}, 0};

    State finalState;
    bool found = false;
    int min_final_cost = 1e9;

    while (!pq.empty()) {
        Node top = pq.top();
        pq.pop();
        
        State u = top.s;
        if (visited[u.l][u.r][u.pos][u.q_idx][u.side]) continue;
        visited[u.l][u.r][u.pos][u.q_idx][u.side] = true;

        if (u.l == 1 && u.r == n && u.q_idx == Lq) {
            if (top.cost < min_final_cost) {
                min_final_cost = top.cost;
                finalState = u;
                found = true;
                break; 
            }
        }

        int cur_row = (u.pos == POS_L) ? u.l : u.r;
        int dL = top.dL;
        int dR = top.dR;

        // Try extending to l-1
        if (u.l > 1) {
            int next_row = u.l - 1;
            int next_pos = POS_L;
            
            int next_q = u.q_idx;
            bool ok_q = true;
            if (pos_in_q[next_row] != -1) {
                if (pos_in_q[next_row] == u.q_idx) next_q++;
                else ok_q = false;
            }
            
            if (ok_q) {
                int move_cost = 0;
                int n_dL = dL, n_dR = dR;
                bool valid_move = false;
                
                if (u.side == SIDE_L) { // Need Left transition
                    if (abs(cur_row - next_row) == 1) {
                        move_cost = 1;
                        valid_move = true;
                    } else {
                        if (dL + 1 <= L - 1) {
                            n_dL++;
                            move_cost = abs(cur_row - next_row) + 2 * n_dL;
                            valid_move = true;
                        }
                    }
                } else { // Need Right transition
                    if (abs(cur_row - next_row) == 1) {
                        move_cost = 1;
                        valid_move = true;
                    } else {
                        if (dR + 1 <= m - R) {
                            n_dR++;
                            move_cost = abs(cur_row - next_row) + 2 * n_dR;
                            valid_move = true;
                        }
                    }
                }

                if (valid_move) {
                    State v = {u.l - 1, u.r, next_pos, next_q, 1 - u.side};
                    int new_cost = top.cost + move_cost + (R - L); 
                    if (new_cost < dist[v.l][v.r][v.pos][v.q_idx][v.side]) {
                        dist[v.l][v.r][v.pos][v.q_idx][v.side] = new_cost;
                        depths[v.l][v.r][v.pos][v.q_idx][v.side] = {n_dL, n_dR};
                        parent[v.l][v.r][v.pos][v.q_idx][v.side] = {u, 1}; 
                        pq.push({new_cost, n_dL, n_dR, v});
                    }
                }
            }
        }

        // Try extending to r+1
        if (u.r < n) {
            int next_row = u.r + 1;
            int next_pos = POS_R;
            
            int next_q = u.q_idx;
            bool ok_q = true;
            if (pos_in_q[next_row] != -1) {
                if (pos_in_q[next_row] == u.q_idx) next_q++;
                else ok_q = false;
            }

            if (ok_q) {
                int move_cost = 0;
                int n_dL = dL, n_dR = dR;
                bool valid_move = false;

                if (u.side == SIDE_L) {
                    if (abs(cur_row - next_row) == 1) {
                        move_cost = 1;
                        valid_move = true;
                    } else {
                        if (dL + 1 <= L - 1) {
                            n_dL++;
                            move_cost = abs(cur_row - next_row) + 2 * n_dL;
                            valid_move = true;
                        }
                    }
                } else {
                    if (abs(cur_row - next_row) == 1) {
                        move_cost = 1;
                        valid_move = true;
                    } else {
                        if (dR + 1 <= m - R) {
                            n_dR++;
                            move_cost = abs(cur_row - next_row) + 2 * n_dR;
                            valid_move = true;
                        }
                    }
                }

                if (valid_move) {
                    State v = {u.l, u.r + 1, next_pos, next_q, 1 - u.side};
                    int new_cost = top.cost + move_cost + (R - L);
                    if (new_cost < dist[v.l][v.r][v.pos][v.q_idx][v.side]) {
                        dist[v.l][v.r][v.pos][v.q_idx][v.side] = new_cost;
                        depths[v.l][v.r][v.pos][v.q_idx][v.side] = {n_dL, n_dR};
                        parent[v.l][v.r][v.pos][v.q_idx][v.side] = {u, 2}; 
                        pq.push({new_cost, n_dL, n_dR, v});
                    }
                }
            }
        }
    }

    if (!found) {
        cout << "NO" << endl;
        return 0;
    }

    cout << "YES" << endl;

    vector<pair<int, int>> path_cells;
    vector<State> states;
    State curr = finalState;
    while (!(curr.l == Sx && curr.r == Sx && curr.q_idx == start_q && curr.side == SIDE_R)) {
        states.push_back(curr);
        curr = parent[curr.l][curr.r][curr.pos][curr.q_idx][curr.side].p_s;
    }
    states.push_back(curr);
    reverse(states.begin(), states.end());

    for (int c = L; c <= R; ++c) path_cells.push_back({Sx, c});
    
    int track_L = 0;
    int track_R = 0;

    for (size_t i = 0; i < states.size() - 1; ++i) {
        State u = states[i];
        State v = states[i + 1];
        
        int u_row = (u.pos == POS_L) ? u.l : u.r;
        int v_row = (v.pos == POS_L) ? v.l : v.r; // Actually check which boundary changed
        // v.l < u.l means l decreased, so v.l is new row
        // v.r > u.r means r increased, so v.r is new row
        int added_row = (v.l < u.l) ? v.l : v.r;
        
        int side = u.side; // 0=R, 1=L
        
        bool jump = (abs(u_row - added_row) > 1);
        int track = 0;
        if (jump) {
            if (side == SIDE_L) track = ++track_L;
            else track = ++track_R;
        }

        if (side == SIDE_L) {
            // From (u_row, L) to (added_row, L)
            if (jump) {
                int col = L - track;
                for (int c = L - 1; c >= col; --c) path_cells.push_back({u_row, c});
                if (u_row < added_row) {
                    for (int r = u_row + 1; r <= added_row; ++r) path_cells.push_back({r, col});
                } else {
                    for (int r = u_row - 1; r >= added_row; --r) path_cells.push_back({r, col});
                }
                for (int c = col + 1; c <= L; ++c) path_cells.push_back({added_row, c});
            } else {
                path_cells.push_back({added_row, L});
            }
            for (int c = L + 1; c <= R; ++c) path_cells.push_back({added_row, c});
        } else {
            // From (u_row, R) to (added_row, R)
            if (jump) {
                int col = R + track;
                for (int c = R + 1; c <= col; ++c) path_cells.push_back({u_row, c});
                if (u_row < added_row) {
                    for (int r = u_row + 1; r <= added_row; ++r) path_cells.push_back({r, col});
                } else {
                    for (int r = u_row - 1; r >= added_row; --r) path_cells.push_back({r, col});
                }
                for (int c = col - 1; c >= R; --c) path_cells.push_back({added_row, c});
            } else {
                path_cells.push_back({added_row, R});
            }
            for (int c = R - 1; c >= L; --c) path_cells.push_back({added_row, c});
        }
    }
    
    cout << path_cells.size() << endl;
    for (auto p : path_cells) {
        cout << p.first << " " << p.second << endl;
    }

    return 0;
}