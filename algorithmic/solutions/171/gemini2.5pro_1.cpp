#include <iostream>
#include <vector>
#include <string>
#include <queue>
#include <cmath>
#include <algorithm>
#include <map>
#include <set>

using namespace std;

struct Point {
    int r, c;
    bool operator<(const Point& other) const {
        if (r != other.r) return r < other.r;
        return c < other.c;
    }
    bool operator==(const Point& other) const {
        return r == other.r && c == other.c;
    }
};

int N, M;
vector<vector<bool>> blocks;

int dr[] = {-1, 1, 0, 0};
int dc[] = {0, 0, -1, 1};
char d_char[] = {'U', 'D', 'L', 'R'};

bool is_valid(int r, int c) {
    return r >= 0 && r < N && c >= 0 && c < N;
}

Point get_neighbor(Point p, int dir_idx) {
    return {p.r + dr[dir_idx], p.c + dc[dir_idx]};
}

Point slide(Point start, int dir_idx) {
    Point current = start;
    while (true) {
        Point next = get_neighbor(current, dir_idx);
        if (!is_valid(next.r, next.c) || blocks[next.r][next.c]) {
            return current;
        }
        current = next;
    }
}

void print_actions(const vector<pair<char, char>>& path) {
    for (const auto& p : path) {
        cout << p.first << " " << p.second << "\n";
    }
}

vector<pair<char, char>> bfs(Point start, Point end) {
    if (start == end) return {};
    vector<vector<Point>> parent(N, vector<Point>(N, {-1, -1}));
    vector<vector<pair<char, char>>> move_to_reach(N, vector<pair<char, char>>(N, {' ', ' '}));
    vector<vector<int>> dist(N, vector<int>(N, -1));
    queue<Point> q;

    q.push(start);
    dist[start.r][start.c] = 0;

    while (!q.empty()) {
        Point curr = q.front();
        q.pop();

        if (curr.r == end.r && curr.c == end.c) break;

        // Moves
        for (int i = 0; i < 4; ++i) {
            Point next = get_neighbor(curr, i);
            if (is_valid(next.r, next.c) && !blocks[next.r][next.c] && dist[next.r][next.c] == -1) {
                dist[next.r][next.c] = dist[curr.r][curr.c] + 1;
                parent[next.r][next.c] = curr;
                move_to_reach[next.r][next.c] = {'M', d_char[i]};
                q.push(next);
            }
        }

        // Slides
        for (int i = 0; i < 4; ++i) {
            Point next = slide(curr, i);
            if ((next.r != curr.r || next.c != curr.c) && dist[next.r][next.c] == -1) {
                dist[next.r][next.c] = dist[curr.r][curr.c] + 1;
                parent[next.r][next.c] = curr;
                move_to_reach[next.r][next.c] = {'S', d_char[i]};
                q.push(next);
            }
        }
    }

    vector<pair<char, char>> path;
    Point curr = end;
    while (!(curr == start)) {
        path.push_back(move_to_reach[curr.r][curr.c]);
        curr = parent[curr.r][curr.c];
    }
    reverse(path.begin(), path.end());
    return path;
}

int manhattan_dist(Point p1, Point p2) {
    return abs(p1.r - p2.r) + abs(p1.c - p2.c);
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    Point initial_pos;
    vector<Point> targets;
    
    cin >> N >> M;
    cin >> initial_pos.r >> initial_pos.c;
    targets.resize(M - 1);
    for (int i = 0; i < M - 1; ++i) {
        cin >> targets[i].r >> targets[i].c;
    }

    vector<vector<int>> desire(N, vector<int>(N, 0));
    set<Point> all_points;
    all_points.insert(initial_pos);
    for (const auto& t : targets) {
        all_points.insert(t);
    }

    for (const auto& t : targets) {
        for (int i = 0; i < 4; ++i) {
            Point neighbor = get_neighbor(t, i);
            if (is_valid(neighbor.r, neighbor.c)) {
                desire[neighbor.r][neighbor.c]++;
            }
        }
    }

    vector<pair<int, Point>> sorted_desire;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            sorted_desire.push_back({desire[i][j], {i, j}});
        }
    }
    sort(sorted_desire.rbegin(), sorted_desire.rend());

    vector<Point> block_locs;
    const int K = 40;
    for (const auto& p : sorted_desire) {
        if (block_locs.size() >= K) break;
        if (all_points.find(p.second) == all_points.end()) {
            block_locs.push_back(p.second);
        }
    }

    Point current_pos = initial_pos;
    blocks.assign(N, vector<bool>(N, false));
    vector<Point> to_place = block_locs;

    while (!to_place.empty()) {
        int best_idx = -1;
        int min_dist = 1e9;

        for (size_t i = 0; i < to_place.size(); ++i) {
            int d = manhattan_dist(current_pos, to_place[i]);
            if (d < min_dist) {
                min_dist = d;
                best_idx = i;
            }
        }
        
        Point block_pos = to_place[best_idx];
        to_place.erase(to_place.begin() + best_idx);

        Point neighbor_to_reach = {-1, -1};
        int min_neighbor_dist = 1e9;
        int best_dir_idx_from_block = -1;

        for (int i = 0; i < 4; ++i) {
            Point neighbor = get_neighbor(block_pos, i);
            if (is_valid(neighbor.r, neighbor.c)) {
                int d = manhattan_dist(current_pos, neighbor);
                if (d < min_neighbor_dist) {
                    min_neighbor_dist = d;
                    neighbor_to_reach = neighbor;
                    best_dir_idx_from_block = i;
                }
            }
        }
        
        vector<pair<char, char>> path = bfs(current_pos, neighbor_to_reach);
        print_actions(path);
        current_pos = neighbor_to_reach;

        char alter_dir = ' ';
        if (best_dir_idx_from_block == 0) alter_dir = 'D'; // From N, place S
        else if (best_dir_idx_from_block == 1) alter_dir = 'U'; // From S, place N
        else if (best_dir_idx_from_block == 2) alter_dir = 'R'; // From W, place E
        else if (best_dir_idx_from_block == 3) alter_dir = 'L'; // From E, place W
        
        cout << "A " << alter_dir << "\n";
        blocks[block_pos.r][block_pos.c] = true;
    }

    Point last_pos = current_pos;
    for(size_t i = 0; i < targets.size(); ++i) {
        vector<pair<char, char>> path = bfs(last_pos, targets[i]);
        print_actions(path);
        last_pos = targets[i];
    }

    return 0;
}