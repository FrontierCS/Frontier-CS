#include <iostream>
#include <vector>
#include <queue>
#include <algorithm>
#include <string>
#include <cstring>
#include <limits>
#include <tuple>
#include <cmath>
#include <set>

using namespace std;

const int INF = 1e9;
const int dx[4] = {-1, 1, 0, 0};
const int dy[4] = {0, 0, -1, 1};
const char dir_char[4] = {'U', 'D', 'L', 'R'};

struct Point {
    int i, j;
    Point(int i=0, int j=0) : i(i), j(j) {}
    bool operator==(const Point& other) const { return i == other.i && j == other.j; }
    bool operator<(const Point& other) const {
        if (i != other.i) return i < other.i;
        return j < other.j;
    }
};

// For Dijkstra
struct DijkstraResult {
    vector<vector<int>> dist;
    vector<vector<int>> prev; // direction from previous cell to current (0-3)
    DijkstraResult(int n, int m) {
        dist.assign(n, vector<int>(m, INF));
        prev.assign(n, vector<int>(m, -1));
    }
};

class HopcroftKarp {
public:
    int L, R;
    vector<vector<int>> adj;
    vector<int> mateL, mateR, dist;
    HopcroftKarp(int L, int R) : L(L), R(R), adj(L) {}
    void addEdge(int u, int v) {
        adj[u].push_back(v);
    }
    bool bfs() {
        queue<int> q;
        dist.assign(L, -1);
        for (int u = 0; u < L; ++u)
            if (mateL[u] == -1) {
                dist[u] = 0;
                q.push(u);
            }
        bool found = false;
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : adj[u]) {
                int u2 = mateR[v];
                if (u2 >= 0 && dist[u2] == -1) {
                    dist[u2] = dist[u] + 1;
                    q.push(u2);
                } else if (u2 == -1) {
                    found = true;
                }
            }
        }
        return found;
    }
    bool dfs(int u) {
        for (int v : adj[u]) {
            int u2 = mateR[v];
            if (u2 == -1 || (dist[u2] == dist[u] + 1 && dfs(u2))) {
                mateL[u] = v;
                mateR[v] = u;
                return true;
            }
        }
        dist[u] = -1;
        return false;
    }
    int maxMatching() {
        mateL.assign(L, -1);
        mateR.assign(R, -1);
        int matching = 0;
        while (bfs()) {
            for (int u = 0; u < L; ++u)
                if (mateL[u] == -1 && dfs(u))
                    matching++;
        }
        return matching;
    }
    void getVertexCover(vector<bool>& inL, vector<bool>& inR) {
        inL.assign(L, false);
        inR.assign(R, false);
        vector<bool> visL(L, false), visR(R, false);
        queue<int> q;
        for (int u = 0; u < L; ++u)
            if (mateL[u] == -1) {
                visL[u] = true;
                q.push(u);
            }
        while (!q.empty()) {
            int u = q.front(); q.pop();
            for (int v : adj[u]) {
                if (!visR[v]) {
                    visR[v] = true;
                    int u2 = mateR[v];
                    if (u2 != -1 && !visL[u2]) {
                        visL[u2] = true;
                        q.push(u2);
                    }
                }
            }
        }
        for (int u = 0; u < L; ++u)
            if (!visL[u]) inL[u] = true;
        for (int v = 0; v < R; ++v)
            if (visR[v]) inR[v] = true;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);

    int N, si, sj;
    cin >> N >> si >> sj;
    vector<string> grid(N);
    for (int i = 0; i < N; ++i) cin >> grid[i];

    vector<vector<int>> weight(N, vector<int>(N, -1));
    vector<Point> road_squares;
    for (int i = 0; i < N; ++i) {
        for (int j = 0; j < N; ++j) {
            if (grid[i][j] != '#') {
                weight[i][j] = grid[i][j] - '0';
                road_squares.emplace_back(i, j);
            }
        }
    }

    // Row segments
    vector<vector<int>> row_id(N, vector<int>(N, -1));
    vector<vector<Point>> row_segments;
    int row_seg_cnt = 0;
    for (int i = 0; i < N; ++i) {
        int j = 0;
        while (j < N) {
            if (weight[i][j] != -1) {
                int start = j;
                while (j < N && weight[i][j] != -1) ++j;
                for (int k = start; k < j; ++k) row_id[i][k] = row_seg_cnt;
                row_segments.emplace_back();
                for (int k = start; k < j; ++k) row_segments.back().emplace_back(i, k);
                ++row_seg_cnt;
            } else {
                ++j;
            }
        }
    }
    int R = row_seg_cnt;

    // Column segments
    vector<vector<int>> col_id(N, vector<int>(N, -1));
    vector<vector<Point>> col_segments;
    int col_seg_cnt = 0;
    for (int j = 0; j < N; ++j) {
        int i = 0;
        while (i < N) {
            if (weight[i][j] != -1) {
                int start = i;
                while (i < N && weight[i][j] != -1) ++i;
                for (int k = start; k < i; ++k) col_id[k][j] = col_seg_cnt;
                col_segments.emplace_back();
                for (int k = start; k < i; ++k) col_segments.back().emplace_back(k, j);
                ++col_seg_cnt;
            } else {
                ++i;
            }
        }
    }
    int C = col_seg_cnt;

    // Build bipartite graph
    HopcroftKarp hk(R, C);
    vector<int> square_r(road_squares.size()), square_c(road_squares.size());
    for (size_t idx = 0; idx < road_squares.size(); ++idx) {
        Point p = road_squares[idx];
        int r = row_id[p.i][p.j];
        int c = col_id[p.i][p.j];
        square_r[idx] = r;
        square_c[idx] = c;
        hk.addEdge(r, c);
    }

    // Maximum matching and vertex cover
    hk.maxMatching();
    vector<bool> inVC_L(R, false), inVC_R(C, false);
    hk.getVertexCover(inVC_L, inVC_R);

    // Greedy set cover to select squares that cover VC segments
    int start_r = row_id[si][sj];
    int start_c = col_id[si][sj];
    vector<bool> covered(R + C, false);
    if (inVC_L[start_r]) covered[start_r] = true;
    if (inVC_R[start_c]) covered[R + start_c] = true;
    set<Point> selected_points;
    selected_points.insert(Point(si, sj));

    // Collect uncovered segment ids
    vector<int> uncovered;
    for (int r = 0; r < R; ++r) if (inVC_L[r] && !covered[r]) uncovered.push_back(r);
    for (int c = 0; c < C; ++c) if (inVC_R[c] && !covered[R + c]) uncovered.push_back(R + c);

    while (!uncovered.empty()) {
        int best_idx = -1;
        int best_cover = 0;
        for (size_t idx = 0; idx < road_squares.size(); ++idx) {
            Point p = road_squares[idx];
            if (selected_points.count(p)) continue;
            int r = square_r[idx];
            int c = square_c[idx];
            int cover_cnt = 0;
            if (inVC_L[r] && !covered[r]) ++cover_cnt;
            if (inVC_R[c] && !covered[R + c]) ++cover_cnt;
            if (cover_cnt > best_cover) {
                best_cover = cover_cnt;
                best_idx = idx;
            }
        }
        if (best_cover == 0) break; // should not happen
        Point best_p = road_squares[best_idx];
        selected_points.insert(best_p);
        int r = square_r[best_idx];
        int c = square_c[best_idx];
        if (inVC_L[r] && !covered[r]) covered[r] = true;
        if (inVC_R[c] && !covered[R + c]) covered[R + c] = true;
        // Recompute uncovered
        uncovered.clear();
        for (int r = 0; r < R; ++r) if (inVC_L[r] && !covered[r]) uncovered.push_back(r);
        for (int c = 0; c < C; ++c) if (inVC_R[c] && !covered[R + c]) uncovered.push_back(R + c);
    }

    // Convert set to vector
    vector<Point> points(selected_points.begin(), selected_points.end());
    int m = points.size();
    if (m == 0) {
        cout << endl;
        return 0;
    }

    // Find start index in points
    int start_idx = -1;
    for (int i = 0; i < m; ++i) {
        if (points[i].i == si && points[i].j == sj) {
            start_idx = i;
            break;
        }
    }

    // Precompute Dijkstra from each point
    vector<DijkstraResult> dijk_results;
    vector<vector<int>> dist_matrix(m, vector<int>(m, INF));
    for (int idx = 0; idx < m; ++idx) {
        Point src = points[idx];
        DijkstraResult res(N, N);
        res.dist[src.i][src.j] = 0;
        using State = tuple<int, int, int>;
        priority_queue<State, vector<State>, greater<State>> pq;
        pq.emplace(0, src.i, src.j);
        while (!pq.empty()) {
            auto [d, i, j] = pq.top(); pq.pop();
            if (d != res.dist[i][j]) continue;
            for (int dir = 0; dir < 4; ++dir) {
                int ni = i + dx[dir];
                int nj = j + dy[dir];
                if (ni < 0 || ni >= N || nj < 0 || nj >= N || weight[ni][nj] == -1) continue;
                int nd = d + weight[ni][nj];
                if (nd < res.dist[ni][nj]) {
                    res.dist[ni][nj] = nd;
                    res.prev[ni][nj] = dir;
                    pq.emplace(nd, ni, nj);
                }
            }
        }
        // Fill distances to other points
        for (int j = 0; j < m; ++j) {
            Point t = points[j];
            dist_matrix[idx][j] = res.dist[t.i][t.j];
        }
        dijk_results.push_back(move(res));
    }

    // Build TSP tour (nearest neighbor)
    vector<int> tour(m);
    vector<bool> visited(m, false);
    tour[0] = start_idx;
    visited[start_idx] = true;
    int current = start_idx;
    for (int i = 1; i < m; ++i) {
        int next = -1;
        int best = INF;
        for (int j = 0; j < m; ++j) {
            if (!visited[j] && dist_matrix[current][j] < best) {
                best = dist_matrix[current][j];
                next = j;
            }
        }
        if (next == -1) break; // should not happen
        tour[i] = next;
        visited[next] = true;
        current = next;
    }

    // 2‑opt improvement
    auto tour_distance = [&](const vector<int>& t) -> double {
        double total = 0;
        for (int i = 0; i < m; ++i) {
            int a = t[i];
            int b = t[(i + 1) % m];
            total += dist_matrix[a][b];
        }
        return total;
    };
    double best_dist = tour_distance(tour);
    bool improved = true;
    while (improved) {
        improved = false;
        for (int i = 0; i < m; ++i) {
            for (int j = i + 1; j < m; ++j) {
                // reverse segment from i+1 to j
                vector<int> new_tour = tour;
                reverse(new_tour.begin() + i + 1, new_tour.begin() + j + 1);
                double new_dist = tour_distance(new_tour);
                if (new_dist < best_dist - 1e-9) {
                    tour = new_tour;
                    best_dist = new_dist;
                    improved = true;
                    break;
                }
            }
            if (improved) break;
        }
    }

    // Generate moves
    string moves;
    for (int i = 0; i < m; ++i) {
        int a = tour[i];
        int b = tour[(i + 1) % m];
        Point src = points[a];
        Point tgt = points[b];
        // Reconstruct path from a to b
        vector<int> path;
        int ci = tgt.i, cj = tgt.j;
        while (!(ci == src.i && cj == src.j)) {
            int dir = dijk_results[a].prev[ci][cj];
            int opp;
            if (dir == 0) opp = 1;
            else if (dir == 1) opp = 0;
            else if (dir == 2) opp = 3;
            else opp = 2;
            path.push_back(opp);
            // Move to previous cell
            if (dir == 0) { ci = ci + 1; }
            else if (dir == 1) { ci = ci - 1; }
            else if (dir == 2) { cj = cj + 1; }
            else { cj = cj - 1; }
        }
        reverse(path.begin(), path.end());
        for (int d : path) moves += dir_char[d];
    }

    cout << moves << endl;
    return 0;
}