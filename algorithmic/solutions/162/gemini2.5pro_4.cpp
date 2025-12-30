#include <iostream>
#include <vector>
#include <utility>
#include <numeric>
#include <algorithm>
#include <queue>
#include <tuple>

using namespace std;

const int N = 30;
vector<vector<int>> b;
vector<pair<int, int>> pos;
vector<tuple<int, int, int, int>> history;

void do_swap(pair<int, int> p1, pair<int, int> p2) {
    int x1 = p1.first, y1 = p1.second;
    int x2 = p2.first, y2 = p2.second;

    int v1 = b[x1][y1];
    int v2 = b[x2][y2];

    swap(b[x1][y1], b[x2][y2]);
    swap(pos[v1], pos[v2]);

    history.emplace_back(x1, y1, x2, y2);
}

pair<int, int> to_axial(pair<int, int> p) {
    return {p.second, p.first - p.second};
}

int dist(pair<int, int> p1, pair<int, int> p2) {
    auto a1 = to_axial(p1);
    auto a2 = to_axial(p2);
    int dq = a2.first - a1.first;
    int dr = a2.second - a1.second;
    if ((long long)dq * dr >= 0) {
        return abs(dq) + abs(dr);
    } else {
        return max(abs(dq), abs(dr));
    }
}

int main() {
    ios_base::sync_with_stdio(false);
    cin.tie(NULL);

    b.resize(N);
    pos.resize(N * (N + 1) / 2);
    for (int i = 0; i < N; ++i) {
        b[i].resize(i + 1);
        for (int j = 0; j <= i; ++j) {
            cin >> b[i][j];
            pos[b[i][j]] = {i, j};
        }
    }

    for (int k = N - 1; k >= 1; --k) {
        int threshold = k * (k + 1) / 2;
        vector<pair<int, int>> L_up, S_down;

        for (int r = 0; r < k; ++r) {
            for (int c = 0; c <= r; ++c) {
                if (b[r][c] >= threshold) {
                    L_up.push_back({r, c});
                }
            }
        }
        for (int c = 0; c <= k; ++c) {
            if (b[k][c] < threshold) {
                S_down.push_back({k, c});
            }
        }

        if (L_up.empty()) continue;

        vector<tuple<int, int, int>> edges;
        for (size_t i = 0; i < L_up.size(); ++i) {
            for (size_t j = 0; j < S_down.size(); ++j) {
                edges.emplace_back(dist(L_up[i], S_down[j]), i, j);
            }
        }
        sort(edges.begin(), edges.end());

        vector<bool> l_used(L_up.size(), false);
        vector<bool> s_used(S_down.size(), false);
        vector<pair<pair<int, int>, pair<int, int>>> pairs;

        for (const auto& edge : edges) {
            int d, l_idx, s_idx;
            tie(d, l_idx, s_idx) = edge;
            if (!l_used[l_idx] && !s_used[s_idx]) {
                pairs.push_back({L_up[l_idx], S_down[s_idx]});
                l_used[l_idx] = true;
                s_used[s_idx] = true;
            }
        }

        for (const auto& p : pairs) {
            pair<int, int> start_pos = p.first;
            pair<int, int> end_pos = p.second;

            vector<vector<pair<int, int>>> parent(N);
            for (int i = 0; i < N; ++i) parent[i].resize(i + 1, {-1, -1});
            
            queue<pair<int, int>> q;
            q.push(end_pos);
            parent[end_pos.first][end_pos.second] = end_pos;

            while (!q.empty()) {
                pair<int, int> curr = q.front();
                q.pop();

                if (curr == start_pos) break;
                
                int x = curr.first, y = curr.second;
                pair<int, int> neighbors[6] = {
                    {x, y - 1}, {x, y + 1}, {x - 1, y - 1},
                    {x - 1, y}, {x + 1, y}, {x + 1, y + 1}
                };
                
                for (auto& next : neighbors) {
                    int nx = next.first, ny = next.second;
                    if (nx >= 0 && nx < N && ny >= 0 && ny <= nx) {
                        if (parent[nx][ny].first == -1) {
                            parent[nx][ny] = curr;
                            q.push(next);
                        }
                    }
                }
            }
            
            vector<pair<int, int>> path;
            pair<int, int> curr = start_pos;
            while (curr != end_pos) {
                path.push_back(curr);
                curr = parent[curr.first][curr.second];
            }
            path.push_back(end_pos);

            for (size_t i = 0; i < path.size() - 2; ++i) {
                do_swap(path[i], path[i+1]);
            }
            if (path.size() >= 2) {
                do_swap(path[path.size()-2], path[path.size()-1]);
            }
            for (int i = path.size() - 3; i >= 0; --i) {
                do_swap(path[i+1], path[i]);
            }
        }
    }

    cout << history.size() << endl;
    for (const auto& t : history) {
        cout << get<0>(t) << " " << get<1>(t) << " " << get<2>(t) << " " << get<3>(t) << endl;
    }

    return 0;
}