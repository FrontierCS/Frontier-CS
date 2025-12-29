#include <bits/stdc++.h>
using namespace std;

struct Point {
    int x, y;
};

// hash for pair<int,int>
struct hash_pair {
    template <class T1, class T2>
    size_t operator()(const pair<T1, T2>& p) const {
        auto hash1 = hash<T1>{}(p.first);
        auto hash2 = hash<T2>{}(p.second);
        return hash1 ^ (hash2 << 1);
    }
};

int main() {
    int N;
    cin >> N;
    vector<Point> points(2 * N);
    for (int i = 0; i < 2 * N; ++i) {
        cin >> points[i].x >> points[i].y;
    }

    const int G = 250;                     // grid cell size
    const int MAXC = 400;                  // 100000 / G = 400
    const int PERIM_LIMIT = 400000;
    const int VERTEX_LIMIT = 1000;

    // grid counts
    vector<vector<int>> M(MAXC, vector<int>(MAXC, 0));
    vector<vector<int>> S(MAXC, vector<int>(MAXC, 0));
    for (int i = 0; i < 2 * N; ++i) {
        int cx = points[i].x / G;
        int cy = points[i].y / G;
        if (cx >= MAXC) cx = MAXC - 1;
        if (cy >= MAXC) cy = MAXC - 1;
        if (i < N)
            M[cx][cy]++;
        else
            S[cx][cy]++;
    }

    // compute D and select cells
    vector<vector<int>> D(MAXC, vector<int>(MAXC, 0));
    vector<vector<bool>> selected(MAXC, vector<bool>(MAXC, false));
    for (int i = 0; i < MAXC; ++i) {
        for (int j = 0; j < MAXC; ++j) {
            D[i][j] = M[i][j] - S[i][j];
            if (D[i][j] > 0)
                selected[i][j] = true;
        }
    }

    // connected components
    vector<vector<int>> comp_id(MAXC, vector<int>(MAXC, -1));
    vector<vector<pair<int, int>>> comp_cells;
    vector<int> comp_totalD;
    int comp_idx = 0;
    const int dx[4] = {1, -1, 0, 0};
    const int dy[4] = {0, 0, 1, -1};

    for (int i = 0; i < MAXC; ++i) {
        for (int j = 0; j < MAXC; ++j) {
            if (selected[i][j] && comp_id[i][j] == -1) {
                queue<pair<int, int>> q;
                q.push({i, j});
                comp_id[i][j] = comp_idx;
                vector<pair<int, int>> cells;
                cells.push_back({i, j});
                int total = D[i][j];

                while (!q.empty()) {
                    auto [x, y] = q.front();
                    q.pop();
                    for (int d = 0; d < 4; ++d) {
                        int nx = x + dx[d];
                        int ny = y + dy[d];
                        if (nx >= 0 && nx < MAXC && ny >= 0 && ny < MAXC &&
                            selected[nx][ny] && comp_id[nx][ny] == -1) {
                            comp_id[nx][ny] = comp_idx;
                            q.push({nx, ny});
                            cells.push_back({nx, ny});
                            total += D[nx][ny];
                        }
                    }
                }
                comp_cells.push_back(cells);
                comp_totalD.push_back(total);
                ++comp_idx;
            }
        }
    }

    // choose the best component
    int best_comp = -1;
    int best_totalD = -1e9;
    for (int i = 0; i < comp_idx; ++i) {
        if (comp_totalD[i] > best_totalD) {
            best_totalD = comp_totalD[i];
            best_comp = i;
        }
    }

    vector<pair<int, int>> poly;  // resulting polygon vertices

    if (best_comp == -1) {
        // fallback: small square around the mackerel with fewest nearby sardines
        const int R = 1000;
        int best_mackerel = -1;
        int min_sard = 1e9;
        for (int i = 0; i < N; ++i) {
            int sard_cnt = 0;
            int x = points[i].x, y = points[i].y;
            for (int j = N; j < 2 * N; ++j) {
                if (abs(x - points[j].x) <= R && abs(y - points[j].y) <= R)
                    ++sard_cnt;
            }
            if (sard_cnt < min_sard) {
                min_sard = sard_cnt;
                best_mackerel = i;
            }
        }
        int x = points[best_mackerel].x;
        int y = points[best_mackerel].y;
        int x1 = max(0, x - 1);
        int y1 = max(0, y - 1);
        int x2 = min(100000, x + 1);
        int y2 = min(100000, y + 1);
        if (x2 - x1 < 1) x2 = x1 + 1;
        if (y2 - y1 < 1) y2 = y1 + 1;
        poly = {{x1, y1}, {x2, y1}, {x2, y2}, {x1, y2}};
    } else {
        // extract boundary edges of the best component
        auto &cells = comp_cells[best_comp];
        vector<tuple<int, int, int>> h_edges;  // (y, x1, x2)
        vector<tuple<int, int, int>> v_edges;  // (x, y1, y2)

        for (auto [i, j] : cells) {
            int x1 = i * G;
            int x2 = (i + 1) * G;
            int y1 = j * G;
            int y2 = (j + 1) * G;

            // up
            if (j + 1 >= MAXC || comp_id[i][j + 1] != best_comp)
                h_edges.emplace_back(y2, x1, x2);
            // down
            if (j - 1 < 0 || comp_id[i][j - 1] != best_comp)
                h_edges.emplace_back(y1, x1, x2);
            // left
            if (i - 1 < 0 || comp_id[i - 1][j] != best_comp)
                v_edges.emplace_back(x1, y1, y2);
            // right
            if (i + 1 >= MAXC || comp_id[i + 1][j] != best_comp)
                v_edges.emplace_back(x2, y1, y2);
        }

        // merge horizontal edges
        sort(h_edges.begin(), h_edges.end());
        vector<tuple<int, int, int>> merged_h;
        for (size_t i = 0; i < h_edges.size();) {
            auto [y, x1, x2] = h_edges[i];
            ++i;
            while (i < h_edges.size()) {
                auto [ny, nx1, nx2] = h_edges[i];
                if (ny == y && nx1 <= x2) {
                    x2 = max(x2, nx2);
                    ++i;
                } else
                    break;
            }
            merged_h.emplace_back(y, x1, x2);
        }

        // merge vertical edges
        sort(v_edges.begin(), v_edges.end());
        vector<tuple<int, int, int>> merged_v;
        for (size_t i = 0; i < v_edges.size();) {
            auto [x, y1, y2] = v_edges[i];
            ++i;
            while (i < v_edges.size()) {
                auto [nx, ny1, ny2] = v_edges[i];
                if (nx == x && ny1 <= y2) {
                    y2 = max(y2, ny2);
                    ++i;
                } else
                    break;
            }
            merged_v.emplace_back(x, y1, y2);
        }

        // build adjacency graph of boundary vertices
        unordered_map<pair<int, int>, vector<pair<int, int>>, hash_pair> adj;
        for (auto [y, x1, x2] : merged_h) {
            pair<int, int> p1 = {x1, y};
            pair<int, int> p2 = {x2, y};
            adj[p1].push_back(p2);
            adj[p2].push_back(p1);
        }
        for (auto [x, y1, y2] : merged_v) {
            pair<int, int> p1 = {x, y1};
            pair<int, int> p2 = {x, y2};
            adj[p1].push_back(p2);
            adj[p2].push_back(p1);
        }

        // extract cycles (boundary loops)
        unordered_set<pair<int, int>, hash_pair> visited;
        vector<vector<pair<int, int>>> cycles;
        for (auto &entry : adj) {
            auto start = entry.first;
            if (visited.count(start)) continue;
            vector<pair<int, int>> cycle;
            auto cur = start;
            pair<int, int> prev = {-1, -1};
            do {
                cycle.push_back(cur);
                visited.insert(cur);
                // find the neighbour that is not the previous vertex
                pair<int, int> next;
                for (auto nb : adj[cur]) {
                    if (nb != prev) {
                        next = nb;
                        break;
                    }
                }
                prev = cur;
                cur = next;
            } while (cur != start);
            cycles.push_back(cycle);
        }

        // choose the cycle with the largest area (outer boundary)
        double max_area = -1;
        vector<pair<int, int>> best_cycle;
        for (auto &cycle : cycles) {
            double area = 0;
            int n = cycle.size();
            for (int i = 0; i < n; ++i) {
                int j = (i + 1) % n;
                area += (double)cycle[i].first * cycle[j].second -
                        (double)cycle[j].first * cycle[i].second;
            }
            area = abs(area) / 2.0;
            if (area > max_area) {
                max_area = area;
                best_cycle = cycle;
            }
        }

        poly = best_cycle;

        // simplify: remove collinear vertices
        bool changed = true;
        while (changed && poly.size() > 4) {
            changed = false;
            vector<pair<int, int>> new_poly;
            int n = poly.size();
            for (int i = 0; i < n; ++i) {
                int prev = (i - 1 + n) % n;
                int next = (i + 1) % n;
                if ((poly[prev].first == poly[i].first &&
                     poly[i].first == poly[next].first) ||
                    (poly[prev].second == poly[i].second &&
                     poly[i].second == poly[next].second)) {
                    changed = true;
                } else {
                    new_poly.push_back(poly[i]);
                }
            }
            poly = new_poly;
        }

        // ensure at least 4 vertices
        if (poly.size() < 4) {
            int minx = 1e9, maxx = -1, miny = 1e9, maxy = -1;
            for (auto [x, y] : poly) {
                minx = min(minx, x);
                maxx = max(maxx, x);
                miny = min(miny, y);
                maxy = max(maxy, y);
            }
            poly.clear();
            poly.push_back({minx, miny});
            poly.push_back({maxx, miny});
            poly.push_back({maxx, maxy});
            poly.push_back({minx, maxy});
        }
    }

    // enforce vertex limit
    if (poly.size() > VERTEX_LIMIT) {
        int minx = 1e9, maxx = -1, miny = 1e9, maxy = -1;
        for (auto [x, y] : poly) {
            minx = min(minx, x);
            maxx = max(maxx, x);
            miny = min(miny, y);
            maxy = max(maxy, y);
        }
        poly.clear();
        poly.push_back({minx, miny});
        poly.push_back({maxx, miny});
        poly.push_back({maxx, maxy});
        poly.push_back({minx, maxy});
    }

    // enforce perimeter limit
    long long perim = 0;
    int m = poly.size();
    for (int i = 0; i < m; ++i) {
        int j = (i + 1) % m;
        perim += abs(poly[i].first - poly[j].first) +
                 abs(poly[i].second - poly[j].second);
    }
    if (perim > PERIM_LIMIT) {
        int minx = 1e9, maxx = -1, miny = 1e9, maxy = -1;
        for (auto [x, y] : poly) {
            minx = min(minx, x);
            maxx = max(maxx, x);
            miny = min(miny, y);
            maxy = max(maxy, y);
        }
        long long bbox_perim = 2LL * ((maxx - minx) + (maxy - miny));
        if (bbox_perim > PERIM_LIMIT) {
            double scale = (double)PERIM_LIMIT / bbox_perim;
            int w = maxx - minx;
            int h = maxy - miny;
            int new_w = (int)(w * scale);
            int new_h = (int)(h * scale);
            int cx = (minx + maxx) / 2;
            int cy = (miny + maxy) / 2;
            minx = cx - new_w / 2;
            maxx = cx + new_w / 2;
            miny = cy - new_h / 2;
            maxy = cy + new_h / 2;
            minx = max(0, minx);
            maxx = min(100000, maxx);
            miny = max(0, miny);
            maxy = min(100000, maxy);
        }
        poly.clear();
        poly.push_back({minx, miny});
        poly.push_back({maxx, miny});
        poly.push_back({maxx, maxy});
        poly.push_back({minx, maxy});
    }

    // output
    cout << poly.size() << "\n";
    for (auto [x, y] : poly) {
        cout << x << " " << y << "\n";
    }

    return 0;
}