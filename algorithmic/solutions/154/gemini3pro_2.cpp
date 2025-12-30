#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <tuple>
#include <cmath>
#include <algorithm>
#include <map>

using namespace std;

// Constants
const int H = 30;
const int W = 30;
const int MAX_TURNS = 300;

// Directions: U, D, L, R
const int DR[] = {-1, 1, 0, 0};
const int DC[] = {0, 0, -1, 1};
const char MOVE_CHARS[] = {'U', 'D', 'L', 'R'};
const char BLOCK_CHARS[] = {'u', 'd', 'l', 'r'};

struct Point {
    int r, c;
    bool operator==(const Point& other) const { return r == other.r && c == other.c; }
    bool operator!=(const Point& other) const { return !(*this == other); }
};

struct Pet {
    int id;
    int r, c;
    int type;
};

struct Human {
    int id;
    int r, c;
};

// Global State
int turn = 0;
bool is_wall[H][W]; // True if blocked (impassable)
vector<Pet> pets;
vector<Human> humans;
int N, M;

// Precomputed logic
bool is_skeleton[H][W];
bool is_hole[H][W];
int room_id[H][W]; // -1 if wall/hole loc, 0..35 for rooms

void init_static_map() {
    for (int r = 0; r < H; ++r) {
        for (int c = 0; c < W; ++c) {
            is_skeleton[r][c] = false;
            is_hole[r][c] = false;
            // Wall lines at 4, 9, 14, 19, 24
            bool r_wall = (r % 5 == 4);
            bool c_wall = (c % 5 == 4);
            
            if (r_wall || c_wall) {
                is_skeleton[r][c] = true;
                // Holes at % 5 == 2
                if (r_wall && c_wall) {
                    is_hole[r][c] = false; // Intersection
                } else if (r_wall) {
                    if (c % 5 == 2) is_hole[r][c] = true;
                } else if (c_wall) {
                    if (r % 5 == 2) is_hole[r][c] = true;
                }
            }
        }
    }

    for (int r = 0; r < H; ++r) {
        for (int c = 0; c < W; ++c) {
            if (is_skeleton[r][c]) {
                room_id[r][c] = -1;
            } else {
                int ri = r / 5;
                int ci = c / 5;
                room_id[r][c] = ri * 6 + ci;
            }
        }
    }
}

bool in_bounds(int r, int c) {
    return r >= 0 && r < H && c >= 0 && c < W;
}

// Check if blocking (r,c) is forbidden by proximity to pets or occupancy
bool can_block(int r, int c, const vector<Pet>& current_pets, const vector<Human>& current_humans) {
    if (!in_bounds(r, c)) return false;
    if (is_wall[r][c]) return false; // Already blocked
    // Check occupancy
    for (const auto& h : current_humans) if (h.r == r && h.c == c) return false;
    for (const auto& p : current_pets) if (p.r == r && p.c == c) return false;

    // Check adjacent to pet
    for (const auto& p : current_pets) {
        if (abs(p.r - r) + abs(p.c - c) <= 1) return false;
    }
    return true;
}

int dist_manhattan(int r1, int c1, int r2, int c2) {
    return abs(r1 - r2) + abs(c1 - c2);
}

// Simple BFS for distance map from a start point to all points
void compute_distances(int start_r, int start_c, int dist_map[H][W], bool avoid_danger) {
    for(int i=0; i<H; ++i) fill(dist_map[i], dist_map[i]+W, 10000);
    queue<Point> q;
    
    dist_map[start_r][start_c] = 0;
    q.push({start_r, start_c});
    
    bool dangerous[H][W];
    for(int i=0; i<H; ++i) fill(dangerous[i], dangerous[i]+W, false);
    if(avoid_danger) {
        for(const auto& p : pets) {
             for(int rr = p.r - 1; rr <= p.r + 1; ++rr) {
                for(int cc = p.c - 1; cc <= p.c + 1; ++cc) {
                    if(in_bounds(rr, cc)) dangerous[rr][cc] = true;
                }
            }
        }
        // If start is dangerous, we must be allowed to leave it, but we can't enter other dangerous spots
        if(dangerous[start_r][start_c]) dangerous[start_r][start_c] = false;
    }

    while(!q.empty()){
        Point u = q.front(); q.pop();
        int d = dist_map[u.r][u.c];
        
        for(int k=0; k<4; ++k){
            int nr = u.r + DR[k];
            int nc = u.c + DC[k];
            if(in_bounds(nr, nc) && !is_wall[nr][nc] && !dangerous[nr][nc]) {
                if(dist_map[nr][nc] > d + 1) {
                    dist_map[nr][nc] = d + 1;
                    q.push({nr, nc});
                }
            }
        }
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);
    init_static_map();

    // Input Initial State
    cin >> N;
    pets.resize(N);
    for (int i = 0; i < N; ++i) {
        cin >> pets[i].r >> pets[i].c >> pets[i].type;
        pets[i].r--; pets[i].c--; // 0-based
        pets[i].id = i;
    }
    cin >> M;
    humans.resize(M);
    for (int i = 0; i < M; ++i) {
        cin >> humans[i].r >> humans[i].c;
        humans[i].r--; humans[i].c--; // 0-based
        humans[i].id = i;
    }

    // Grid Init
    for (int r = 0; r < H; ++r) for (int c = 0; c < W; ++c) is_wall[r][c] = false;

    for (turn = 0; turn < MAX_TURNS; ++turn) {
        string actions = "";
        
        // For each human, decide the best action greedily
        for (int i = 0; i < M; ++i) {
            Human& h = humans[i];
            
            // Compute distances to unbuilt skeleton walls
            int dist_to_skel[H][W];
            compute_distances(h.r, h.c, dist_to_skel, false);
            
            double best_score = -1e9;
            char best_act = '.';
            
            // Evaluate all 9 possible actions
            // 0: Stay
            // 1-4: Move
            // 5-8: Block
            for (int k = 0; k < 9; ++k) {
                char act = '.';
                int nr = h.r, nc = h.c;
                bool is_move = false;
                bool is_block = false;
                Point block_target = {-1, -1};
                
                if (k == 0) { act = '.'; }
                else if (k <= 4) { 
                    act = MOVE_CHARS[k-1]; 
                    nr += DR[k-1]; nc += DC[k-1]; 
                    is_move = true; 
                }
                else { 
                    act = BLOCK_CHARS[k-5]; 
                    block_target = {h.r + DR[k-5], h.c + DC[k-5]}; 
                    is_block = true; 
                }
                
                // Validity Checks
                if (is_move) {
                    if (!in_bounds(nr, nc) || is_wall[nr][nc]) continue;
                }
                if (is_block) {
                    if (!can_block(block_target.r, block_target.c, pets, humans)) continue;
                }

                // Score Calculation
                double score = 0;
                
                // 1. Safety Score: Distance to pets
                int closest_pet = 1000;
                for(auto& p : pets) {
                    int d = dist_manhattan(nr, nc, p.r, p.c);
                    if(d < closest_pet) closest_pet = d;
                }
                
                // If extremely close, huge penalty
                if (closest_pet <= 2) score -= 10000; 
                else if (closest_pet <= 4) score -= (5 - closest_pet) * 500;
                
                // 2. Action Utility
                if (is_block) {
                    int br = block_target.r, bc = block_target.c;
                    if (is_skeleton[br][bc]) {
                        if (!is_hole[br][bc]) {
                            score += 200; // Build main skeleton
                        } else {
                            // Hole Logic: close if pets are nearby but not too close
                            int pets_nearby = 0;
                            for(auto& p : pets) if(dist_manhattan(br, bc, p.r, p.c) < 10) pets_nearby++;
                            
                            if (pets_nearby > 0) {
                                score += 300; // Close hole to seal
                            } else {
                                score -= 50; // Keep open
                            }
                        }
                    } else {
                        score -= 200; // Don't build random walls
                    }
                } else {
                    // Move/Stay Score
                    // Heuristic: move closer to unbuilt skeleton walls
                    // Find min distance to an unbuilt skeleton from (nr, nc)
                    // We approximate using the BFS from h.r:
                    // If moving to (nr,nc) decreases dist to ANY unbuilt skeleton, good.
                    // But that requires BFS from every target. Too slow.
                    // Instead use BFS from h.r: if dist_to_skel[nr][nc] < dist_to_skel[h.r][h.c] -> moving away? 
                    // No, `dist_to_skel` computed distance FROM h.r.
                    // We need distance TO skeleton.
                    // Let's iterate all skeleton cells and find closest one.
                    int min_s_dist = 1000;
                    for(int r=0; r<H; ++r) {
                        for(int c=0; c<W; ++c) {
                            if(is_skeleton[r][c] && !is_wall[r][c] && !is_hole[r][c]) {
                                int d = dist_manhattan(nr, nc, r, c);
                                if(d < min_s_dist) min_s_dist = d;
                            }
                        }
                    }
                    // Reward minimizing distance to skeleton
                    score -= min_s_dist * 10;
                    
                    // Small penalty for staying to encourage action
                    if (!is_block && nr == h.r && nc == h.c) {
                        score -= 5;
                    }
                }
                
                // Tie-break
                score += (k * 0.1);

                if (score > best_score) {
                    best_score = score;
                    best_act = act;
                }
            }
            actions += best_act;
        }

        cout << actions << endl;

        // Process Pet Moves
        string pet_moves;
        for(int i=0; i<N; ++i) {
            cin >> pet_moves;
            for(char c : pet_moves) {
                int dir = -1;
                if(c == 'U') dir=0;
                else if(c == 'D') dir=1;
                else if(c == 'L') dir=2;
                else if(c == 'R') dir=3;
                
                if(dir != -1) {
                    pets[i].r += DR[dir];
                    pets[i].c += DC[dir];
                }
            }
        }

        // Apply new walls
        for(int i=0; i<M; ++i) {
            char act = actions[i];
            if (act >= 'a' && act <= 'z') {
                int dir = -1;
                if(act=='u') dir=0; else if(act=='d') dir=1; else if(act=='l') dir=2; else if(act=='r') dir=3;
                int br = humans[i].r + DR[dir];
                int bc = humans[i].c + DC[dir];
                is_wall[br][bc] = true;
            }
        }
        
        // Apply human moves
        for(int i=0; i<M; ++i) {
            char act = actions[i];
            if (act >= 'A' && act <= 'Z') {
                int dir = -1;
                if(act=='U') dir=0; else if(act=='D') dir=1; else if(act=='L') dir=2; else if(act=='R') dir=3;
                int nr = humans[i].r + DR[dir];
                int nc = humans[i].c + DC[dir];
                if (in_bounds(nr, nc) && !is_wall[nr][nc]) {
                    humans[i].r = nr;
                    humans[i].c = nc;
                }
            }
        }
    }
    
    return 0;
}