#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <map>
#include <cmath>
#include <algorithm>

using namespace std;

const int N = 20;
int M;

struct Pos {
    int r, c;
    bool operator<(const Pos& other) const {
        if (r != other.r) return r < other.r;
        return c < other.c;
    }
    bool operator==(const Pos& other) const {
        return r == other.r && c == other.c;
    }
};

int manhattan(Pos p1, Pos p2) {
    return abs(p1.r - p2.r) + abs(p1.c - p2.c);
}

vector<Pos> targets;
vector<vector<bool>> has_block;
Pos current_pos;
vector<pair<char, char>> actions;

int dr[] = {-1, 1, 0, 0};
int dc[] = {0, 0, -1, 1};
char d_char[] = {'U', 'D', 'L', 'R'};

bool is_valid(int r, int c) {
    return r >= 0 && r < N && c >= 0 && c < N;
}

void do_action(char action, char dir) {
    actions.push_back({action, dir});
    int d_idx = -1;
    for (int i = 0; i < 4; ++i) {
        if (d_char[i] == dir) {
            d_idx = i;
            break;
        }
    }

    if (action == 'A') {
        int nr = current_pos.r + dr[d_idx];
        int nc = current_pos.c + dc[d_idx];
        if (is_valid(nr, nc)) {
            has_block[nr][nc] = !has_block[nr][nc];
        }
    } else if (action == 'M') {
        current_pos.r += dr[d_idx];
        current_pos.c += dc[d_idx];
    } else if (action == 'S') {
        Pos p = current_pos;
        while (true) {
            int r = p.r + dr[d_idx];
            int c = p.c + dc[d_idx];
            if (!is_valid(r, c) || has_block[r][c]) {
                break;
            }
            p = {r, c};
        }
        current_pos = p;
    }
}

void move_to(Pos target) {
    while (current_pos.c < target.c) do_action('M', 'R');
    while (current_pos.c > target.c) do_action('M', 'L');
    while (current_pos.r < target.r) do_action('M', 'D');
    while (current_pos.r > target.r) do_action('M', 'U');
}

void execute_path(const vector<Pos>& path) {
    for (size_t i = 1; i < path.size(); ++i) {
        Pos prev = path[i - 1];
        Pos curr = path[i];
        if (abs(prev.r - curr.r) + abs(prev.c - curr.c) == 1) { // Move
            if (curr.r == prev.r - 1) do_action('M', 'U');
            else if (curr.r == prev.r + 1) do_action('M', 'D');
            else if (curr.c == prev.c - 1) do_action('M', 'L');
            else do_action('M', 'R');
        } else { // Slide
            if (curr.r < prev.r) do_action('S', 'U');
            else if (curr.r > prev.r) do_action('S', 'D');
            else if (curr.c < prev.c) do_action('S', 'L');
            else do_action('S', 'R');
        }
    }
}

vector<Pos> bfs(Pos start, Pos end) {
    vector<vector<Pos>> parent(N, vector<Pos>(N, {-1, -1}));
    vector<vector<int>> dist(N, vector<int>(N, -1));
    queue<Pos> q;

    q.push(start);
    dist[start.r][start.c] = 0;

    while (!q.empty()) {
        Pos u = q.front();
        q.pop();

        if (u.r == end.r && u.c == end.c) break;

        // Moves
        for (int i = 0; i < 4; ++i) {
            int nr = u.r + dr[i];
            int nc = u.c + dc[i];
            if (is_valid(nr, nc) && !has_block[nr][nc] && dist[nr][nc] == -1) {
                dist[nr][nc] = dist[u.r][u.c] + 1;
                parent[nr][nc] = u;
                q.push({nr, nc});
            }
        }

        // Slides
        for (int i = 0; i < 4; ++i) {
            Pos p = u;
            while (true) {
                int r = p.r + dr[i];
                int c = p.c + dc[i];
                if (!is_valid(r, c) || has_block[r][c]) {
                    break;
                }
                p = {r, c};
            }
            if ((p.r != u.r || p.c != u.c) && dist[p.r][p.c] == -1) {
                dist[p.r][p.c] = dist[u.r][u.c] + 1;
                parent[p.r][p.c] = u;
                q.push(p);
            }
        }
    }
    
    vector<Pos> path;
    if (dist[end.r][end.c] != -1) {
        Pos curr = end;
        while (curr.r != -1) {
            path.push_back(curr);
            if (parent[curr.r][curr.c].r == -1) break;
            curr = parent[curr.r][curr.c];
        }
        reverse(path.begin(), path.end());
    }
    return path;
}


int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    int n_dummy;
    cin >> n_dummy >> M;
    targets.resize(M);
    for (int i = 0; i < M; ++i) {
        cin >> targets[i].r >> targets[i].c;
    }

    current_pos = targets[0];
    has_block.assign(N, vector<bool>(N, false));

    map<Pos, int> scores;
    for (int i = 1; i < M; ++i) {
        Pos prev = targets[i - 1];
        Pos curr = targets[i];
        if (curr.r > prev.r && is_valid(curr.r + 1, curr.c)) scores[{curr.r + 1, curr.c}]++;
        if (curr.r < prev.r && is_valid(curr.r - 1, curr.c)) scores[{curr.r - 1, curr.c}]++;
        if (curr.c > prev.c && is_valid(curr.r, curr.c + 1)) scores[{curr.r, curr.c + 1}]++;
        if (curr.c < prev.c && is_valid(curr.r, curr.c - 1)) scores[{curr.r, curr.c - 1}]++;
    }

    vector<pair<int, Pos>> sorted_scores;
    for (auto const& [pos, score] : scores) {
        sorted_scores.push_back({-score, pos});
    }
    sort(sorted_scores.begin(), sorted_scores.end());

    vector<Pos> blocks_to_place;
    int K = 35;
    for (int i = 0; i < min((int)sorted_scores.size(), K); ++i) {
        if (sorted_scores[i].first <= -2) {
             if (!(sorted_scores[i].second == targets[0])) {
                blocks_to_place.push_back(sorted_scores[i].second);
            }
        }
    }
    
    vector<bool> placed_mask(blocks_to_place.size(), false);
    int placed_count = 0;
    while(placed_count < blocks_to_place.size()) {
        int best_idx = -1;
        int min_dist = 1e9;
        Pos best_neighbor;

        for (int i = 0; i < blocks_to_place.size(); ++i) {
            if (placed_mask[i]) continue;
            Pos b_pos = blocks_to_place[i];
            for (int d = 0; d < 4; ++d) {
                Pos n_pos = {b_pos.r - dr[d], b_pos.c - dc[d]};
                if (is_valid(n_pos.r, n_pos.c) && !has_block[n_pos.r][n_pos.c]) {
                     int dist = manhattan(current_pos, n_pos);
                     if (dist < min_dist) {
                         min_dist = dist;
                         best_idx = i;
                         best_neighbor = n_pos;
                     }
                }
            }
        }
        
        if (best_idx == -1) break; 

        move_to(best_neighbor);
        Pos b_pos = blocks_to_place[best_idx];
        if (b_pos.r == best_neighbor.r + 1) do_action('A', 'D');
        else if (b_pos.r == best_neighbor.r - 1) do_action('A', 'U');
        else if (b_pos.c == best_neighbor.c + 1) do_action('A', 'R');
        else do_action('A', 'L');

        placed_mask[best_idx] = true;
        placed_count++;
    }


    for (int i = 1; i < M; ++i) {
        Pos target = targets[i];
        if (has_block[target.r][target.c]) {
            Pos best_neighbor = {-1, -1};
            int min_dist = 1e9;
            for (int d = 0; d < 4; ++d) {
                Pos n_pos = {target.r + dr[d], target.c + dc[d]};
                if (is_valid(n_pos.r, n_pos.c) && !has_block[n_pos.r][n_pos.c]) {
                    int dist = manhattan(current_pos, n_pos);
                    if (dist < min_dist) {
                        min_dist = dist;
                        best_neighbor = n_pos;
                    }
                }
            }
            if (best_neighbor.r != -1) {
                move_to(best_neighbor);
                if (target.r == best_neighbor.r + 1) do_action('A', 'D');
                else if (target.r == best_neighbor.r - 1) do_action('A', 'U');
                else if (target.c == best_neighbor.c + 1) do_action('A', 'R');
                else do_action('A', 'L');
            }
        }
        
        vector<Pos> path = bfs(current_pos, target);
        if (path.empty()) {
            move_to(target);
        } else {
            execute_path(path);
        }
    }
    
    for(const auto& p : actions) {
        cout << p.first << " " << p.second << "\n";
    }

    return 0;
}