#include <iostream>
#include <vector>
#include <deque>
#include <queue>
#include <algorithm>
#include <cmath>
#include <cstring>
#include <unordered_set>
#include <tuple>

using namespace std;

struct Point {
    int x, y;
    bool operator==(const Point& other) const {
        return x == other.x && y == other.y;
    }
};

namespace std {
    template<> struct hash<Point> {
        size_t operator()(const Point& p) const {
            return p.x * 31 + p.y;
        }
    };
}

int N, M;
vector<Point> pet_pos;
vector<int> pet_type;
vector<Point> human_pos;

vector<vector<bool>> blocked(31, vector<bool>(31, false));
vector<Point> wall_squares;
vector<Point> approach_squares;
vector<bool> wall_built;
deque<int> wall_queue;

int chosen_B, chosen_R;
const int MAX_STUCK = 10;

// For each human
vector<int> target_wall_idx(M, -1);
vector<int> stuck_count(M, 0);

// Directions
const int dx[4] = {-1, 1, 0, 0};
const int dy[4] = {0, 0, -1, 1};
const char dir_char[4] = {'U', 'D', 'L', 'R'};
const char block_char[4] = {'u', 'd', 'l', 'r'};

// Grid for wall indices
vector<vector<int>> wall_index(31, vector<int>(31, -1));

void choose_rectangle() {
    double best_score = -1;
    int best_B = 2, best_R = 2;
    for (int B = 2; B <= 30; ++B) {
        for (int R = 2; R <= 30; ++R) {
            int area = B * R;
            int pet_count = 0;
            for (const auto& p : pet_pos) {
                if (p.x <= B && p.y <= R) pet_count++;
            }
            double score = area * pow(0.5, pet_count);
            if (score > best_score) {
                best_score = score;
                best_B = B;
                best_R = R;
            }
        }
    }
    chosen_B = best_B;
    chosen_R = best_R;
}

void generate_walls() {
    // Right wall: (i, chosen_R) for i=1..chosen_B
    for (int i = 1; i <= chosen_B; ++i) {
        wall_squares.push_back({i, chosen_R});
        approach_squares.push_back({i, chosen_R - 1});
    }
    // Bottom wall: (chosen_B, j) for j=1..chosen_R-1
    for (int j = 1; j <= chosen_R - 1; ++j) {
        wall_squares.push_back({chosen_B, j});
        approach_squares.push_back({chosen_B - 1, j});
    }
    int sz = wall_squares.size();
    wall_built.assign(sz, false);
    for (int i = 0; i < sz; ++i) {
        const Point& w = wall_squares[i];
        wall_index[w.x][w.y] = i;
        wall_queue.push_back(i);
    }
}

// BFS to find first step from start to target, avoiding forbidden squares
// Returns direction index (0..3) or -1 if no path.
int bfs(const Point& start, const Point& target, const vector<vector<bool>>& forbid) {
    if (start.x == target.x && start.y == target.y) return -1;
    vector<vector<bool>> visited(31, vector<bool>(31, false));
    vector<vector<Point>> parent(31, vector<Point>(31, {-1,-1}));
    queue<Point> q;
    q.push(start);
    visited[start.x][start.y] = true;
    while (!q.empty()) {
        Point p = q.front(); q.pop();
        for (int d = 0; d < 4; ++d) {
            int nx = p.x + dx[d];
            int ny = p.y + dy[d];
            if (nx < 1 || nx > 30 || ny < 1 || ny > 30) continue;
            if (visited[nx][ny]) continue;
            if (forbid[nx][ny]) continue;
            visited[nx][ny] = true;
            parent[nx][ny] = p;
            if (nx == target.x && ny == target.y) {
                // backtrack to first step
                Point cur = {nx, ny};
                while (!(parent[cur.x][cur.y].x == start.x && parent[cur.x][cur.y].y == start.y)) {
                    cur = parent[cur.x][cur.y];
                }
                // cur is the first step from start
                for (int d2 = 0; d2 < 4; ++d2) {
                    if (start.x + dx[d2] == cur.x && start.y + dy[d2] == cur.y) {
                        return d2;
                    }
                }
            }
            q.push({nx, ny});
        }
    }
    return -1;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    // Input
    cin >> N;
    pet_pos.resize(N);
    pet_type.resize(N);
    for (int i = 0; i < N; ++i) {
        cin >> pet_pos[i].x >> pet_pos[i].y >> pet_type[i];
    }
    cin >> M;
    human_pos.resize(M);
    for (int i = 0; i < M; ++i) {
        cin >> human_pos[i].x >> human_pos[i].y;
    }

    // Initialize strategy
    choose_rectangle();
    generate_walls();
    target_wall_idx.assign(M, -1);
    stuck_count.assign(M, 0);

    // Main loop
    for (int turn = 0; turn < 300; ++turn) {
        vector<char> actions(M, '.');
        unordered_set<Point> blocked_now; // squares to be blocked this turn
        vector<int> blocked_human_idx(M, -1); // which wall index human i will block, -1 if none

        // For each human, decide action
        for (int i = 0; i < M; ++i) {
            while (true) {
                if (target_wall_idx[i] == -1) {
                    if (wall_queue.empty()) {
                        actions[i] = '.';
                        break;
                    }
                    target_wall_idx[i] = wall_queue.front();
                    wall_queue.pop_front();
                    stuck_count[i] = 0;
                }
                int idx = target_wall_idx[i];
                Point wall = wall_squares[idx];
                Point approach = approach_squares[idx];

                // If wall already built (by someone else), release and try again
                if (blocked[wall.x][wall.y]) {
                    target_wall_idx[i] = -1;
                    continue;
                }

                // Check if human is at approach position
                if (human_pos[i].x == approach.x && human_pos[i].y == approach.y) {
                    // Check if we can block
                    bool can_block = true;
                    // Wall square must not contain pet or human at start of turn
                    for (const auto& p : pet_pos) {
                        if (p.x == wall.x && p.y == wall.y) { can_block = false; break; }
                    }
                    for (int j = 0; j < M; ++j) {
                        if (human_pos[j].x == wall.x && human_pos[j].y == wall.y) { can_block = false; break; }
                    }
                    // Adjacent squares must not contain pets
                    for (int d = 0; d < 4 && can_block; ++d) {
                        int nx = wall.x + dx[d], ny = wall.y + dy[d];
                        if (nx < 1 || nx > 30 || ny < 1 || ny > 30) continue;
                        for (const auto& p : pet_pos) {
                            if (p.x == nx && p.y == ny) { can_block = false; break; }
                        }
                    }
                    // Must not be already blocked this turn
                    if (blocked_now.find(wall) != blocked_now.end()) can_block = false;

                    if (can_block) {
                        // Determine direction from human to wall
                        int dir = -1;
                        if (wall.x > approach.x) dir = 1;      // down
                        else if (wall.x < approach.x) dir = 0; // up
                        else if (wall.y > approach.y) dir = 3; // right
                        else dir = 2; // left
                        actions[i] = block_char[dir];
                        blocked_now.insert(wall);
                        blocked_human_idx[i] = idx;
                        target_wall_idx[i] = -1; // released after blocking
                        stuck_count[i] = 0;
                        break;
                    } else {
                        // Cannot block this turn
                        stuck_count[i]++;
                        if (stuck_count[i] > MAX_STUCK) {
                            // Release this wall back to queue
                            wall_queue.push_back(idx);
                            target_wall_idx[i] = -1;
                            stuck_count[i] = 0;
                            continue;
                        } else {
                            actions[i] = '.';
                            break;
                        }
                    }
                } else {
                    // Not at approach: move towards it
                    // Build forbid grid for BFS
                    vector<vector<bool>> forbid(31, vector<bool>(31, false));
                    for (int x = 1; x <= 30; ++x) {
                        for (int y = 1; y <= 30; ++y) {
                            if (blocked[x][y]) forbid[x][y] = true;
                        }
                    }
                    for (const Point& p : blocked_now) forbid[p.x][p.y] = true;
                    // Mark all unbuilt wall squares as forbidden
                    for (int k = 0; k < (int)wall_squares.size(); ++k) {
                        if (!wall_built[k]) {
                            Point w = wall_squares[k];
                            forbid[w.x][w.y] = true;
                        }
                    }
                    // BFS
                    int dir = bfs(human_pos[i], approach, forbid);
                    if (dir != -1) {
                        actions[i] = dir_char[dir];
                        stuck_count[i] = 0;
                    } else {
                        actions[i] = '.';
                        stuck_count[i]++;
                        if (stuck_count[i] > MAX_STUCK) {
                            wall_queue.push_back(idx);
                            target_wall_idx[i] = -1;
                            stuck_count[i] = 0;
                            continue;
                        }
                    }
                    break;
                }
            }
        }

        // Output actions
        for (int i = 0; i < M; ++i) {
            cout << actions[i];
        }
        cout << endl;
        cout.flush();

        // Update human positions (move)
        vector<Point> next_human_pos = human_pos;
        for (int i = 0; i < M; ++i) {
            if (actions[i] == 'U') next_human_pos[i].x--;
            else if (actions[i] == 'D') next_human_pos[i].x++;
            else if (actions[i] == 'L') next_human_pos[i].y--;
            else if (actions[i] == 'R') next_human_pos[i].y++;
        }
        human_pos = next_human_pos;

        // Update blocked squares from successful blocks
        for (int i = 0; i < M; ++i) {
            if (blocked_human_idx[i] != -1) {
                int idx = blocked_human_idx[i];
                Point wall = wall_squares[idx];
                blocked[wall.x][wall.y] = true;
                wall_built[idx] = true;
            }
        }

        // Read pet movements
        for (int i = 0; i < N; ++i) {
            string s;
            cin >> s;
            // Update pet position according to s
            Point& p = pet_pos[i];
            for (char c : s) {
                if (c == 'U') p.x--;
                else if (c == 'D') p.x++;
                else if (c == 'L') p.y--;
                else if (c == 'R') p.y++;
            }
        }
    }

    return 0;
}