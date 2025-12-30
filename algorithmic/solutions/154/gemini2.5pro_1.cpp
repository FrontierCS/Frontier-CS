#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <cmath>
#include <algorithm>
#include <map>

const int GRID_SIZE = 30;
const int TURN_LIMIT = 300;

struct Point {
    int r, c;

    bool operator==(const Point& other) const {
        return r == other.r && c == other.c;
    }
    bool operator!=(const Point& other) const {
        return !(*this == other);
    }
    bool operator<(const Point& other) const {
        if (r != other.r) return r < other.r;
        return c < other.c;
    }
};

long long dist_sq(Point p1, Point p2) {
    long long dr = p1.r - p2.r;
    long long dc = p1.c - p2.c;
    return dr * dr + dc * dc;
}

int dist_manhattan(Point p1, Point p2) {
    return std::abs(p1.r - p2.r) + std::abs(p1.c - p2.c);
}

struct Pet {
    Point pos;
    int type;
};

struct Human {
    int id;
    Point pos;
    std::vector<Point> wall_targets;
};

int N, M;
std::vector<Pet> pets;
std::vector<Human> humans;
int grid[GRID_SIZE][GRID_SIZE];

const int dr[] = {-1, 1, 0, 0};
const int dc[] = {0, 0, -1, 1};
const char move_chars[] = {'U', 'D', 'L', 'R'};
const char build_chars[] = {'u', 'd', 'l', 'r'};

bool is_valid(int r, int c) {
    return r >= 0 && r < GRID_SIZE && c >= 0 && c < GRID_SIZE;
}

char get_move_to_neighbor(Point from, Point to) {
    for (int i = 0; i < 4; ++i) {
        if (from.r + dr[i] == to.r && from.c + dc[i] == to.c) {
            return move_chars[i];
        }
    }
    return '.';
}

char get_build_at_neighbor(Point from, Point to) {
    for (int i = 0; i < 4; ++i) {
        if (from.r + dr[i] == to.r && from.c + dc[i] == to.c) {
            return build_chars[i];
        }
    }
    return '.';
}

char get_move_towards(Point start, Point end, const int current_grid[GRID_SIZE][GRID_SIZE]) {
    if (start == end) return '.';
    
    std::queue<Point> q;
    q.push(start);
    Point parent[GRID_SIZE][GRID_SIZE];
    bool visited[GRID_SIZE][GRID_SIZE] = {};
    visited[start.r][start.c] = true;

    Point path_end = {-1, -1};

    while (!q.empty()) {
        Point curr = q.front();
        q.pop();

        if (curr == end) {
            path_end = curr;
            break;
        }

        for (int i = 0; i < 4; ++i) {
            int nr = curr.r + dr[i];
            int nc = curr.c + dc[i];
            if (is_valid(nr, nc) && !visited[nr][nc] && current_grid[nr][nc] == 0) {
                visited[nr][nc] = true;
                parent[nr][nc] = curr;
                q.push({nr, nc});
            }
        }
    }

    if (path_end.r != -1) {
        Point p = path_end;
        if (p == start) return '.';
        while (parent[p.r][p.c] != start) {
            p = parent[p.r][p.c];
        }
        return get_move_to_neighbor(start, p);
    }
    
    return '.';
}

bool is_safe_to_build(Point p, const bool pet_at[GRID_SIZE][GRID_SIZE], const bool human_at[GRID_SIZE][GRID_SIZE]) {
    if (!is_valid(p.r, p.c) || grid[p.r][p.c] != 0) return false;
    if (pet_at[p.r][p.c] || human_at[p.r][p.c]) return false;
    for (int i = 0; i < 4; ++i) {
        int nr = p.r + dr[i];
        int nc = p.c + dc[i];
        if (is_valid(nr, nc) && pet_at[nr][nc]) return false;
    }
    return true;
}

int main() {
    std::ios_base::sync_with_stdio(false);
    std::cin.tie(NULL);

    std::cin >> N;
    pets.resize(N);
    for (int i = 0; i < N; ++i) {
        std::cin >> pets[i].pos.r >> pets[i].pos.c >> pets[i].type;
        pets[i].pos.r--; pets[i].pos.c--;
    }
    std::cin >> M;
    humans.resize(M);
    for (int i = 0; i < M; ++i) {
        humans[i].id = i;
        std::cin >> humans[i].pos.r >> humans[i].pos.c;
        humans[i].pos.r--; humans[i].pos.c--;
    }

    const int ENCLOSURE_SIZE = 17;
    Point corners[4] = {{0, 0}, {0, GRID_SIZE - ENCLOSURE_SIZE}, {GRID_SIZE - ENCLOSURE_SIZE, 0}, {GRID_SIZE - ENCLOSURE_SIZE, GRID_SIZE - ENCLOSURE_SIZE}};
    Point centers[4] = {
        {ENCLOSURE_SIZE / 2, ENCLOSURE_SIZE / 2},
        {ENCLOSURE_SIZE / 2, GRID_SIZE - ENCLOSURE_SIZE + ENCLOSURE_SIZE / 2},
        {GRID_SIZE - ENCLOSURE_SIZE + ENCLOSURE_SIZE / 2, ENCLOSURE_SIZE / 2},
        {GRID_SIZE - ENCLOSURE_SIZE + ENCLOSURE_SIZE / 2, GRID_SIZE - ENCLOSURE_SIZE + ENCLOSURE_SIZE / 2}
    };
    
    long long best_cost = -1;
    int best_corner_idx = 0;
    for (int i = 0; i < 4; ++i) {
        long long current_cost = 0;
        for (const auto& pet : pets) {
            current_cost += dist_sq(pet.pos, centers[i]);
        }
        if (current_cost > best_cost) {
            best_cost = current_cost;
            best_corner_idx = i;
        }
    }

    Point enclosure_tl = corners[best_corner_idx];
    Point safe_spot = centers[best_corner_idx];

    std::vector<Point> wall_segments;
    int r_wall = (enclosure_tl.r == 0) ? ENCLOSURE_SIZE : enclosure_tl.r - 1;
    int c_wall = (enclosure_tl.c == 0) ? ENCLOSURE_SIZE : enclosure_tl.c - 1;

    for (int c = enclosure_tl.c; c < enclosure_tl.c + ENCLOSURE_SIZE; ++c) {
        wall_segments.push_back({r_wall, c});
    }
    for (int r = enclosure_tl.r; r < enclosure_tl.r + ENCLOSURE_SIZE; ++r) {
        wall_segments.push_back({r, c_wall});
    }
    
    std::sort(wall_segments.begin(), wall_segments.end());
    wall_segments.erase(std::unique(wall_segments.begin(), wall_segments.end()), wall_segments.end());

    for(size_t i = 0; i < wall_segments.size(); ++i) {
        humans[i % M].wall_targets.push_back(wall_segments[i]);
    }
    
    for (int i = 0; i < M; ++i) {
        if(humans[i].wall_targets.empty()) continue;
        Point current_pos = humans[i].pos;
        std::vector<Point> sorted_targets;
        std::vector<bool> used(humans[i].wall_targets.size(), false);
        for(size_t j = 0; j < humans[i].wall_targets.size(); ++j) {
            int best_k = -1;
            int min_d = 1e9;
            for(size_t k = 0; k < humans[i].wall_targets.size(); ++k) {
                if(!used[k]) {
                    int d = dist_manhattan(current_pos, humans[i].wall_targets[k]);
                    if (d < min_d) {
                        min_d = d;
                        best_k = k;
                    }
                }
            }
            if (best_k != -1) {
                Point next_target = humans[i].wall_targets[best_k];
                sorted_targets.push_back(next_target);
                used[best_k] = true;
                current_pos = next_target;
            }
        }
        humans[i].wall_targets = sorted_targets;
    }


    for (int t = 0; t < TURN_LIMIT; ++t) {
        std::string actions(M, '.');
        
        bool pet_at[GRID_SIZE][GRID_SIZE] = {};
        for(const auto& pet : pets) {
            pet_at[pet.pos.r][pet.pos.c] = true;
        }
        bool human_at[GRID_SIZE][GRID_SIZE] = {};
        for(const auto& human : humans) {
            human_at[human.pos.r][human.pos.c] = true;
        }

        for (int i = 0; i < M; ++i) {
            Point move_target_pos;
            bool is_moving = false;

            if (humans[i].wall_targets.empty()) {
                move_target_pos = safe_spot;
                is_moving = true;
            } else {
                Point wall_target = humans[i].wall_targets.front();
                
                Point build_spot = {-1, -1};
                int min_dist = 1e9;

                for (int j = 0; j < 4; ++j) {
                    int nr = wall_target.r + dr[j];
                    int nc = wall_target.c + dc[j];
                    if (is_valid(nr, nc) && grid[nr][nc] == 0) {
                        int d = dist_manhattan(humans[i].pos, {nr, nc});
                        if (d < min_dist) {
                            min_dist = d;
                            build_spot = {nr, nc};
                        }
                    }
                }

                if (build_spot.r != -1) {
                    if (humans[i].pos == build_spot) {
                        if (is_safe_to_build(wall_target, pet_at, human_at)) {
                            actions[i] = get_build_at_neighbor(humans[i].pos, wall_target);
                        } else {
                            actions[i] = '.';
                        }
                    } else {
                        move_target_pos = build_spot;
                        is_moving = true;
                    }
                } else {
                    actions[i] = '.';
                }
            }
            if (is_moving) {
                actions[i] = get_move_towards(humans[i].pos, move_target_pos, grid);
            }
        }

        std::cout << actions << std::endl;

        for (int i = 0; i < M; ++i) {
            char action = actions[i];
            if (action >= 'a' && action <= 'z') {
                int dir_idx = -1;
                for(int j=0; j<4; ++j) if(build_chars[j] == action) dir_idx = j;
                int nr = humans[i].pos.r + dr[dir_idx];
                int nc = humans[i].pos.c + dc[dir_idx];
                if (is_valid(nr, nc)) grid[nr][nc] = 1;
                if (!humans[i].wall_targets.empty()) humans[i].wall_targets.erase(humans[i].wall_targets.begin());
            } else if (action >= 'A' && action <= 'Z') {
                int dir_idx = -1;
                for(int j=0; j<4; ++j) if(move_chars[j] == action) dir_idx = j;
                humans[i].pos.r += dr[dir_idx];
                humans[i].pos.c += dc[dir_idx];
            }
        }
        
        for (int i = 0; i < N; ++i) {
            std::string pet_move;
            std::cin >> pet_move;
            if (pet_move != ".") {
                for (char move : pet_move) {
                    if (move == 'U') pets[i].pos.r--;
                    else if (move == 'D') pets[i].pos.r++;
                    else if (move == 'L') pets[i].pos.c--;
                    else if (move == 'R') pets[i].pos.c++;
                }
            }
        }
    }

    return 0;
}