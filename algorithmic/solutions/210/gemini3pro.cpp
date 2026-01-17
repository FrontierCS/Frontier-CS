#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <algorithm>
#include <cmath>

using namespace std;

// Data structures
struct Point {
    int r, c;
    bool operator==(const Point& o) const { return r == o.r && c == o.c; }
    bool operator!=(const Point& o) const { return !(*this == o); }
};

struct BlueBase {
    int id;
    Point p;
    int fuel, missiles;
};

struct RedBase {
    int id;
    Point p;
    int defense, value;
    int current_defense;
    bool destroyed;
    bool targeted; 
    int assigned_fighter_id;
};

struct Fighter {
    int id;
    Point p;
    int G_cap, C_cap;
    int fuel, missiles;
    
    enum State { IDLE, MOVING_TO_BASE, REFUELING, MOVING_TO_TARGET, ATTACKING };
    State state;
    
    int target_rb;
    int target_bb;
    vector<int> path; 
    int path_idx;
};

// Globals
int N, M, K;
vector<string> grid;
vector<BlueBase> blue_bases;
vector<RedBase> red_bases;
vector<Fighter> fighters;

// Direction mapping: 0:up, 1:down, 2:left, 3:right
int dr[] = {-1, 1, 0, 0};
int dc[] = {0, 0, -1, 1}; 

bool in_bounds(int r, int c) {
    return r >= 0 && r < N && c >= 0 && c < M;
}

// BFS Pathfinding
// If adjacent_stop is true, we stop when adjacent to dest (for attacking red bases)
// Grid cells with '#' are obstacles
vector<int> get_path(Point start, Point dest, bool adjacent_stop) {
    // If start is dest
    if (start == dest && !adjacent_stop) return {};
    // If need adjacent and already adjacent
    if (adjacent_stop && abs(start.r - dest.r) + abs(start.c - dest.c) == 1) return {};

    queue<Point> q;
    q.push(start);
    vector<vector<int>> dist_map(N, vector<int>(M, -1));
    vector<vector<int>> parent_dir(N, vector<int>(M, -1));
    dist_map[start.r][start.c] = 0;
    
    Point end_node = {-1, -1};
    bool found = false;

    while(!q.empty()) {
        Point u = q.front(); q.pop();

        if (adjacent_stop) {
            if (abs(u.r - dest.r) + abs(u.c - dest.c) == 1) {
                end_node = u;
                found = true;
                break;
            }
        } else {
            if (u == dest) {
                end_node = u;
                found = true;
                break;
            }
        }

        for(int i=0; i<4; ++i) {
            int nr = u.r + dr[i];
            int nc = u.c + dc[i];
            
            if (in_bounds(nr, nc) && dist_map[nr][nc] == -1) {
                // Check obstacle
                if (grid[nr][nc] != '#') {
                    dist_map[nr][nc] = dist_map[u.r][u.c] + 1;
                    parent_dir[nr][nc] = i;
                    q.push({nr, nc});
                }
            }
        }
    }

    if (!found) return {};

    // Reconstruct path
    vector<int> path;
    Point curr = end_node;
    while(curr != start) {
        int dir = parent_dir[curr.r][curr.c];
        path.push_back(dir);
        // Backtrack
        if(dir == 0) curr.r++;
        else if(dir == 1) curr.r--;
        else if(dir == 2) curr.c++;
        else if(dir == 3) curr.c--;
    }
    reverse(path.begin(), path.end());
    return path;
}

int main() {
    // Optimization for fast I/O
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N >> M)) return 0;
    grid.resize(N);
    for(int i=0; i<N; ++i) cin >> grid[i];

    int nb; cin >> nb;
    for(int i=0; i<nb; ++i) {
        BlueBase b; b.id = i;
        cin >> b.p.r >> b.p.c;
        int d, v;
        cin >> b.fuel >> b.missiles >> d >> v;
        blue_bases.push_back(b);
    }

    int nr; cin >> nr;
    for(int i=0; i<nr; ++i) {
        RedBase b; b.id = i;
        cin >> b.p.r >> b.p.c;
        int dummy_g, dummy_c;
        cin >> dummy_g >> dummy_c >> b.defense >> b.value;
        b.current_defense = b.defense;
        b.destroyed = false;
        b.targeted = false;
        b.assigned_fighter_id = -1;
        red_bases.push_back(b);
    }

    cin >> K;
    for(int i=0; i<K; ++i) {
        Fighter f; f.id = i;
        cin >> f.p.r >> f.p.c >> f.G_cap >> f.C_cap;
        f.fuel = 0; f.missiles = 0;
        f.state = Fighter::IDLE;
        f.target_rb = -1;
        f.target_bb = -1;
        fighters.push_back(f);
    }

    // Simulation loop
    for (int frame = 0; frame < 15000; ++frame) {
        bool any_alive = false;
        for(const auto& rb : red_bases) if(!rb.destroyed) any_alive = true;
        
        if(!any_alive) {
            cout << "OK" << endl;
            continue;
        }

        for (int i = 0; i < K; ++i) {
            Fighter &f = fighters[i];

            // --- State: IDLE ---
            if (f.state == Fighter::IDLE) {
                int best_rb = -1;
                int best_bb = -1;
                double best_val = -1.0;

                // Simple greedy assignment: Value / Distance
                for (int r=0; r<nr; ++r) {
                    if (red_bases[r].destroyed) continue;
                    // Prefer untargeted bases to spread out fighters
                    if (red_bases[r].targeted && red_bases[r].assigned_fighter_id != f.id) continue;

                    // Find best supply base
                    for (int b=0; b<nb; ++b) {
                        if (blue_bases[b].fuel <= 0) continue; 
                        
                        int dist = abs(blue_bases[b].p.r - red_bases[r].p.r) + abs(blue_bases[b].p.c - red_bases[r].p.c);
                        // Safety margin for fuel: round trip + buffer
                        if (2 * dist + 10 > f.G_cap) continue; 

                        double score = (double)red_bases[r].value / (dist + 1);
                        // Bonus for low health?
                        // score *= (1.0 + 1000.0/red_bases[r].current_defense);

                        if (score > best_val) {
                            best_val = score;
                            best_rb = r;
                            best_bb = b;
                        }
                    }
                }

                // If no ideal target, help any alive target (multiple fighters on one base)
                if (best_rb == -1) {
                     for (int r=0; r<nr; ++r) {
                        if (red_bases[r].destroyed) continue;
                        for (int b=0; b<nb; ++b) {
                            if (blue_bases[b].fuel <= 0) continue;
                            int dist = abs(blue_bases[b].p.r - red_bases[r].p.r) + abs(blue_bases[b].p.c - red_bases[r].p.c);
                            if (2 * dist + 10 > f.G_cap) continue;
                            best_rb = r; best_bb = b; break; 
                        }
                        if (best_rb != -1) break;
                     }
                }

                if (best_rb != -1) {
                    f.target_rb = best_rb;
                    f.target_bb = best_bb;
                    red_bases[best_rb].targeted = true;
                    red_bases[best_rb].assigned_fighter_id = f.id;

                    f.state = Fighter::MOVING_TO_BASE;
                    f.path = get_path(f.p, blue_bases[best_bb].p, false);
                    f.path_idx = 0;
                    // If path empty but not at base? Should not happen with valid logic/maps
                }
            }
            // Use else-if to prevent multiple moves per frame, but allow logical transitions

            // --- State: MOVING_TO_BASE ---
            else if (f.state == Fighter::MOVING_TO_BASE) {
                // Check if arrived
                if (f.p == blue_bases[f.target_bb].p) {
                    f.state = Fighter::REFUELING;
                } else {
                    if (f.path_idx < f.path.size()) {
                        int dir = f.path[f.path_idx];
                        if (f.fuel > 0) {
                            cout << "move " << f.id << " " << dir << endl;
                            f.fuel--;
                            if(dir==0) f.p.r--; else if(dir==1) f.p.r++; else if(dir==2) f.p.c--; else f.p.c++;
                            f.path_idx++;
                        } else {
                            // Emergency: stuck without fuel. Check if accidentally at a base
                             bool at_base = false;
                             for(auto &bb : blue_bases) {
                                 if(bb.p == f.p) {
                                     f.target_bb = bb.id;
                                     f.state = Fighter::REFUELING;
                                     at_base = true;
                                     break;
                                 }
                             }
                             if(!at_base) f.state = Fighter::IDLE; // Fail
                        }
                    } else {
                        // Path finished
                        if (f.p == blue_bases[f.target_bb].p) f.state = Fighter::REFUELING;
                        else {
                            // Path recalculation needed
                            f.path = get_path(f.p, blue_bases[f.target_bb].p, false);
                            f.path_idx = 0;
                            if (f.path.empty() && f.p != blue_bases[f.target_bb].p) f.state = Fighter::IDLE;
                        }
                    }
                }
            }

            // --- State: REFUELING ---
            else if (f.state == Fighter::REFUELING) {
                BlueBase &bb = blue_bases[f.target_bb];
                RedBase &rb = red_bases[f.target_rb];

                // Calculate path to target for fuel estimation
                vector<int> p_att = get_path(f.p, rb.p, true);
                if (p_att.empty() && (abs(f.p.r - rb.p.r) + abs(f.p.c - rb.p.c) != 1)) {
                    f.state = Fighter::IDLE;
                    rb.targeted = false;
                    rb.assigned_fighter_id = -1;
                } else {
                    int dist = p_att.size();
                    int req_fuel = min(f.G_cap, dist * 2 + 10);
                    int cur_def = rb.destroyed ? 0 : rb.current_defense;
                    int req_mis = min(f.C_cap, cur_def);

                    int fuel_load = max(0, req_fuel - f.fuel);
                    if (fuel_load > bb.fuel) fuel_load = bb.fuel;
                    
                    if (fuel_load > 0) {
                        cout << "fuel " << f.id << " " << fuel_load << endl;
                        f.fuel += fuel_load;
                        bb.fuel -= fuel_load;
                    }

                    int mis_load = max(0, req_mis - f.missiles);
                    if (mis_load > bb.missiles) mis_load = bb.missiles;

                    if (mis_load > 0) {
                        cout << "missile " << f.id << " " << mis_load << endl;
                        f.missiles += mis_load;
                        bb.missiles -= mis_load;
                    }

                    // Check if ready to depart
                    if (f.fuel >= dist && f.missiles > 0) {
                        f.path = p_att;
                        f.path_idx = 0;
                        f.state = Fighter::MOVING_TO_TARGET;
                    } else {
                        // Not enough resources in this base, give up and try another
                        f.state = Fighter::IDLE;
                    }
                }
            }

            // --- State: MOVING_TO_TARGET ---
            else if (f.state == Fighter::MOVING_TO_TARGET) {
                 if (f.path_idx < f.path.size()) {
                     int dir = f.path[f.path_idx];
                     if (f.fuel > 0) {
                         cout << "move " << f.id << " " << dir << endl;
                         f.fuel--;
                         if(dir==0) f.p.r--; else if(dir==1) f.p.r++; else if(dir==2) f.p.c--; else f.p.c++;
                         f.path_idx++;
                     } else {
                         f.state = Fighter::IDLE;
                     }
                 } else {
                     f.state = Fighter::ATTACKING;
                 }
            }

            // --- State: ATTACKING ---
            else if (f.state == Fighter::ATTACKING) {
                RedBase &rb = red_bases[f.target_rb];
                if (rb.destroyed) {
                    f.state = Fighter::IDLE;
                } else {
                    int adir = -1;
                    for(int k=0; k<4; ++k) {
                        if (f.p.r + dr[k] == rb.p.r && f.p.c + dc[k] == rb.p.c) {
                            adir = k; break;
                        }
                    }

                    if (adir != -1) {
                        if (f.missiles > 0) {
                            int cnt = min(f.missiles, rb.current_defense);
                            cout << "attack " << f.id << " " << adir << " " << cnt << endl;
                            f.missiles -= cnt;
                            rb.current_defense -= cnt;
                            if (rb.current_defense <= 0) {
                                rb.destroyed = true;
                                grid[rb.p.r][rb.p.c] = '.';
                                f.state = Fighter::IDLE;
                            }
                        } else {
                            // Out of ammo, go back to reload
                            f.state = Fighter::IDLE;
                            rb.targeted = false; 
                            rb.assigned_fighter_id = -1;
                        }
                    } else {
                        // Not adjacent, path adjustment needed
                        f.path = get_path(f.p, rb.p, true);
                        f.path_idx = 0;
                        if(f.path.empty() && (abs(f.p.r - rb.p.r) + abs(f.p.c - rb.p.c) != 1)) {
                             f.state = Fighter::IDLE;
                        } else {
                            f.state = Fighter::MOVING_TO_TARGET;
                        }
                    }
                }
            }
        }
        cout << "OK" << endl;
    }

    return 0;
}