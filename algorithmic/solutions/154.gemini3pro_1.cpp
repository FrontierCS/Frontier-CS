#include <iostream>
#include <vector>
#include <string>
#include <cmath>
#include <algorithm>
#include <queue>
#include <set>
#include <map>

using namespace std;

// Coordinate structure
struct Point {
    int r, c;
    bool operator==(const Point& other) const { return r == other.r && c == other.c; }
    bool operator!=(const Point& other) const { return !(*this == other); }
    bool operator<(const Point& other) const {
        if (r != other.r) return r < other.r;
        return c < other.c;
    }
};

struct Pet {
    Point p;
    int type;
};

int N, M;
vector<Pet> pets;
vector<Point> humans;
int grid_state[32][32]; // 0: empty, 1: blocked

// Grid configuration
const int GRID_SIZE = 30;
// We define walls at these rows and columns to partition the grid
const vector<int> LINES = {5, 10, 15, 20, 25};
bool is_wall_site[32][32];
bool is_gate_site[32][32];
int region_id[32][32];
bool region_has_pet[36];

// Directions
int dr[] = {-1, 1, 0, 0};
int dc[] = {0, 0, -1, 1};
char dchar[] = {'U', 'D', 'L', 'R'};
char bchar[] = {'u', 'd', 'l', 'r'};

// Check if coordinates are within the board
bool valid(int r, int c) {
    return r >= 1 && r <= GRID_SIZE && c >= 1 && c <= GRID_SIZE;
}

int dist_manhattan(Point p1, Point p2) {
    return abs(p1.r - p2.r) + abs(p1.c - p2.c);
}

// Initialize the target wall structure
void init_grid_layout() {
    for (int r = 1; r <= 30; ++r) {
        for (int c = 1; c <= 30; ++c) {
            is_wall_site[r][c] = false;
            is_gate_site[r][c] = false;
            region_id[r][c] = -1;
        }
    }

    // Mark wall lines
    for (int r : LINES) {
        for (int c = 1; c <= 30; ++c) is_wall_site[r][c] = true;
    }
    for (int c : LINES) {
        for (int r = 1; r <= 30; ++r) is_wall_site[r][c] = true;
    }

    // Assign regions (areas between walls)
    // Intervals are 1-4, 6-9, 11-14, 16-19, 21-24, 26-30
    vector<pair<int, int>> intervals = {{1, 4}, {6, 9}, {11, 14}, {16, 19}, {21, 24}, {26, 30}};
    
    int r_idx = 0;
    for (auto& row_int : intervals) {
        int c_idx = 0;
        for (auto& col_int : intervals) {
            int reg = r_idx * 6 + c_idx;
            for (int r = row_int.first; r <= row_int.second; ++r) {
                for (int c = col_int.first; c <= col_int.second; ++c) {
                    region_id[r][c] = reg;
                }
            }
            c_idx++;
        }
        r_idx++;
    }

    // Define gates (holes in walls to keep connectivity initially)
    for (int r : LINES) {
        for (auto& interval : intervals) {
            int len = interval.second - interval.first + 1;
            int mid = interval.first + len / 2;
            is_gate_site[r][mid] = true;
        }
    }
    for (int c : LINES) {
        for (auto& interval : intervals) {
            int len = interval.second - interval.first + 1;
            int mid = interval.first + len / 2;
            is_gate_site[mid][c] = true;
        }
    }
}

// Check if any pet is within distance 1 of (r, c)
// This covers both "pet at (r,c)" and "pet adjacent to (r,c)"
bool has_pet_neighbor(int r, int c) {
    for (const auto& pet : pets) {
        if (dist_manhattan({r, c}, pet.p) <= 1) return true;
    }
    return false;
}

// Determine which regions contain pets
void update_region_status() {
    for (int i = 0; i < 36; ++i) region_has_pet[i] = false;
    for (const auto& pet : pets) {
        int r = pet.p.r;
        int c = pet.p.c;
        if (!is_wall_site[r][c]) {
            if (region_id[r][c] != -1)
                region_has_pet[region_id[r][c]] = true;
        } else {
            // If pet is on a wall, it contaminates adjacent regions
            for (int k = 0; k < 4; ++k) {
                int nr = r + dr[k];
                int nc = c + dc[k];
                if (valid(nr, nc) && !is_wall_site[nr][nc] && region_id[nr][nc] != -1) {
                    region_has_pet[region_id[nr][nc]] = true;
                }
            }
        }
    }
}

// Identify which regions are separated by a gate
pair<int, int> get_regions_connected_by_gate(int r, int c) {
    int r1 = -1, r2 = -1;
    for (int k = 0; k < 4; ++k) {
        int nr = r + dr[k];
        int nc = c + dc[k];
        if (valid(nr, nc) && !is_wall_site[nr][nc] && region_id[nr][nc] != -1) {
            if (r1 == -1) r1 = region_id[nr][nc];
            else if (r1 != region_id[nr][nc]) r2 = region_id[nr][nc];
        }
    }
    return {r1, r2};
}

int main() {
    // Optimize I/O operations
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    if (!(cin >> N)) return 0;
    pets.resize(N);
    for (int i = 0; i < N; ++i) {
        cin >> pets[i].p.r >> pets[i].p.c >> pets[i].type;
    }
    cin >> M;
    humans.resize(M);
    for (int i = 0; i < M; ++i) {
        cin >> humans[i].p.r >> humans[i].p.c;
    }

    init_grid_layout();

    for (int turn = 0; turn < 300; ++turn) {
        update_region_status();

        string actions = "";
        vector<Point> next_human_pos = humans;
        set<Point> reserved_blocks; // Keep track of blocks planned in this turn

        for (int i = 0; i < M; ++i) {
            Point p = humans[i];
            
            // Find best wall candidate
            double max_wall_val = -1e9;
            Point best_wall = {-1, -1};

            for (int r = 1; r <= 30; ++r) {
                for (int c = 1; c <= 30; ++c) {
                    // Consider unbuilt wall sites
                    if (is_wall_site[r][c] && grid_state[r][c] == 0) {
                        // Safety check: Cannot build if pets are near
                        if (has_pet_neighbor(r, c)) continue;
                        
                        // Check if occupied by pet (already covered by has_pet_neighbor, but good for clarity)
                        bool occupied = false;
                        for(auto& pe : pets) if(pe.p.r == r && pe.p.c == c) occupied = true;
                        if(occupied) continue; 

                        double val = 0;
                        if (is_gate_site[r][c]) {
                            // Logic for gates: Close if it connects to a pet-infested region
                            pair<int, int> regs = get_regions_connected_by_gate(r, c);
                            bool r1_bad = (regs.first != -1 && region_has_pet[regs.first]);
                            bool r2_bad = (regs.second != -1 && region_has_pet[regs.second]);
                            
                            if (r1_bad || r2_bad) val = 200; // High priority to seal
                            else val = -5000; // Keep open to maintain connectivity
                        } else {
                            val = 100; // Regular walls have standard priority
                        }

                        // Heuristic scoring: Value - Cost (Distance)
                        int dist = dist_manhattan(p, {r, c});
                        int move_cost = max(0, dist - 1); // Cost to reach neighbor
                        double score = val - move_cost * 2.0 - 0.01 * dist;

                        if (score > max_wall_val) {
                            max_wall_val = score;
                            best_wall = {r, c};
                        }
                    }
                }
            }

            char best_act = '.';
            
            // If adjacent to the best target, try to block it
            if (best_wall.r != -1 && dist_manhattan(p, best_wall) == 1) {
                bool ok = true;
                // Don't block if human is on it (shouldn't happen with grid_state==0 check usually, but safe)
                for (auto& h : humans) if (h.r == best_wall.r && h.c == best_wall.c) ok = false;
                // Don't block if pet is on it
                for (auto& pe : pets) if (pe.p.r == best_wall.r && pe.p.c == best_wall.c) ok = false;
                // Don't block if pet adjacent
                if (has_pet_neighbor(best_wall.r, best_wall.c)) ok = false;
                // Don't block if already planned by another human
                if (reserved_blocks.count(best_wall)) ok = false;

                if (ok) {
                    for (int k = 0; k < 4; ++k) {
                        if (p.r + dr[k] == best_wall.r && p.c + dc[k] == best_wall.c) {
                            best_act = bchar[k];
                            reserved_blocks.insert(best_wall);
                            goto chosen;
                        }
                    }
                }
            }

            // Move towards best target (or escape/roam if no target)
            if (best_wall.r != -1) {
                int min_d = 1e9;
                int best_k = -1;
                
                for (int k = 0; k < 4; ++k) {
                    int nr = p.r + dr[k];
                    int nc = p.c + dc[k];
                    if (valid(nr, nc) && grid_state[nr][nc] == 0) {
                        // Avoid moving into a square that is being blocked
                        if (reserved_blocks.count({nr, nc})) continue;
                        
                        int d = dist_manhattan({nr, nc}, best_wall);
                        int safety_penalty = 0;
                        if (has_pet_neighbor(nr, nc)) safety_penalty = 1000; // Penalize getting close to pets
                        
                        if (d + safety_penalty < min_d) {
                            min_d = d + safety_penalty;
                            best_k = k;
                        }
                    }
                }
                
                if (best_k != -1 && min_d < 1000) {
                     best_act = dchar[best_k];
                } else if (best_k != -1 && has_pet_neighbor(p.r, p.c)) {
                    // If currently in danger, force move even if destination is somewhat dangerous
                    best_act = dchar[best_k];
                }
            } else {
                // No valid wall to build, just avoid pets
                if (has_pet_neighbor(p.r, p.c)) {
                    for (int k = 0; k < 4; ++k) {
                        int nr = p.r + dr[k];
                        int nc = p.c + dc[k];
                        if (valid(nr, nc) && grid_state[nr][nc] == 0 && !reserved_blocks.count({nr, nc})) {
                            if (!has_pet_neighbor(nr, nc)) {
                                best_act = dchar[k];
                                break;
                            }
                        }
                    }
                }
            }
            
            chosen:
            actions += best_act;
            // Update state for subsequent humans in the same turn (greedy coordination)
            if (best_act >= 'a' && best_act <= 'z') {
                 for(int k=0; k<4; ++k) if(bchar[k] == best_act) {
                     reserved_blocks.insert({p.r + dr[k], p.c + dc[k]});
                 }
            } else if (best_act != '.') {
                 for(int k=0; k<4; ++k) if(dchar[k] == best_act) {
                     next_human_pos[i] = {p.r + dr[k], p.c + dc[k]};
                 }
            }
        }

        cout << actions << endl;
        
        // Update local state
        humans = next_human_pos;
        for (auto pt : reserved_blocks) {
            grid_state[pt.r][pt.c] = 1;
        }

        // Read pet moves and update positions
        for (int i = 0; i < N; ++i) {
            string move_seq;
            cin >> move_seq;
            for (char c : move_seq) {
                for (int k = 0; k < 4; ++k) {
                    if (dchar[k] == c) {
                        pets[i].p.r += dr[k];
                        pets[i].p.c += dc[k];
                        break;
                    }
                }
            }
        }
    }

    return 0;
}