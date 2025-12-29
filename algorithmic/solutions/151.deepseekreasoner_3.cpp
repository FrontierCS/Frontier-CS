#include <bits/stdc++.h>
using namespace std;

struct Point {
    int i, j;
    Point(int i=0, int j=0) : i(i), j(j) {}
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(0);

    int N, si, sj;
    cin >> N >> si >> sj;
    vector<string> grid(N);
    for(int i=0; i<N; i++) cin >> grid[i];

    vector<vector<int>> cost(N, vector<int>(N, 0));
    vector<vector<bool>> road(N, vector<bool>(N, false));
    for(int i=0; i<N; i++) {
        for(int j=0; j<N; j++) {
            if(grid[i][j] != '#') {
                road[i][j] = true;
                cost[i][j] = grid[i][j] - '0';
            }
        }
    }

    vector<vector<int>> h_id(N, vector<int>(N, -1));
    struct HSeg { int i, l, r; };
    vector<HSeg> h_seg_list;
    int cur_h_id = 0;
    for(int i=0; i<N; i++) {
        int j = 0;
        while(j < N) {
            if(road[i][j]) {
                int l = j;
                while(j < N && road[i][j]) j++;
                int r = j-1;
                for(int k=l; k<=r; k++) h_id[i][k] = cur_h_id;
                h_seg_list.push_back({i, l, r});
                cur_h_id++;
            } else j++;
        }
    }
    int H = cur_h_id;

    vector<vector<int>> v_id(N, vector<int>(N, -1));
    vector<HSeg> v_seg_list;
    int cur_v_id = 0;
    for(int j=0; j<N; j++) {
        int i = 0;
        while(i < N) {
            if(road[i][j]) {
                int l = i;
                while(i < N && road[i][j]) i++;
                int r = i-1;
                for(int k=l; k<=r; k++) v_id[k][j] = cur_v_id;
                v_seg_list.push_back({j, l, r});
                cur_v_id++;
            } else i++;
        }
    }
    int V = cur_v_id;

    vector<vector<int>> adj(H);
    for(int i=0; i<N; i++) {
        for(int j=0; j<N; j++) {
            if(road[i][j]) {
                int h = h_id[i][j];
                int v = v_id[i][j];
                adj[h].push_back(v);
            }
        }
    }

    vector<int> matchL(H, -1), matchR(V, -1);
    vector<int> distH(H);
    auto bfs = [&]() -> bool {
        queue<int> q;
        for(int u=0; u<H; u++) {
            if(matchL[u] == -1) {
                distH[u] = 0;
                q.push(u);
            } else distH[u] = -1;
        }
        bool found = false;
        while(!q.empty()) {
            int u = q.front(); q.pop();
            for(int v : adj[u]) {
                int u2 = matchR[v];
                if(u2 != -1 && distH[u2] == -1) {
                    distH[u2] = distH[u] + 1;
                    q.push(u2);
                } else if(u2 == -1) found = true;
            }
        }
        return found;
    };
    function<bool(int)> dfs = [&](int u) -> bool {
        for(int v : adj[u]) {
            int u2 = matchR[v];
            if(u2 == -1 || (distH[u2] == distH[u] + 1 && dfs(u2))) {
                matchL[u] = v;
                matchR[v] = u;
                return true;
            }
        }
        distH[u] = -1;
        return false;
    };
    while(bfs()) {
        for(int u=0; u<H; u++)
            if(matchL[u] == -1 && dfs(u)) {}
    }

    vector<bool> visL(H, false), visR(V, false);
    function<void(int)> dfs_alt = [&](int u) {
        visL[u] = true;
        for(int v : adj[u]) {
            if(visR[v]) continue;
            visR[v] = true;
            if(matchR[v] != -1) dfs_alt(matchR[v]);
        }
    };
    for(int u=0; u<H; u++)
        if(matchL[u] == -1) dfs_alt(u);

    vector<bool> inC_H(H, false), inC_V(V, false);
    for(int u=0; u<H; u++) if(!visL[u]) inC_H[u] = true;
    for(int v=0; v<V; v++) if(visR[v])   inC_V[v] = true;

    vector<int> seg_ids;
    unordered_map<int, int> seg_to_idx;
    for(int h=0; h<H; h++) {
        if(inC_H[h]) {
            seg_to_idx[h] = seg_ids.size();
            seg_ids.push_back(h);
        }
    }
    for(int v=0; v<V; v++) {
        if(inC_V[v]) {
            int id = H + v;
            seg_to_idx[id] = seg_ids.size();
            seg_ids.push_back(id);
        }
    }
    int m = seg_ids.size();

    vector<vector<int>> square_cover;
    vector<Point> squares_list;
    vector<int> square_h_id, square_v_id;
    vector<vector<int>> sq_index(N, vector<int>(N, -1));
    int sq_counter = 0;
    for(int i=0; i<N; i++) {
        for(int j=0; j<N; j++) {
            if(road[i][j]) {
                sq_index[i][j] = sq_counter;
                squares_list.push_back(Point(i,j));
                square_h_id.push_back(h_id[i][j]);
                square_v_id.push_back(v_id[i][j]);
                vector<int> cov;
                int h = h_id[i][j];
                int v = v_id[i][j];
                if(inC_H[h]) cov.push_back(seg_to_idx[h]);
                if(inC_V[v]) cov.push_back(seg_to_idx[H + v]);
                square_cover.push_back(cov);
                sq_counter++;
            }
        }
    }
    int total_squares = sq_counter;

    vector<bool> covered_seg(m, false);
    vector<bool> selected_sq(total_squares, false);
    vector<Point> S_points;
    int covered_count = 0;
    while(covered_count < m) {
        int best_sq = -1, best_cnt = -1;
        for(int idx=0; idx<total_squares; idx++) {
            if(selected_sq[idx]) continue;
            int cnt = 0;
            for(int seg_idx : square_cover[idx])
                if(!covered_seg[seg_idx]) cnt++;
            if(cnt > best_cnt) {
                best_cnt = cnt;
                best_sq = idx;
            }
        }
        if(best_sq == -1) break;
        selected_sq[best_sq] = true;
        S_points.push_back(squares_list[best_sq]);
        for(int seg_idx : square_cover[best_sq]) {
            if(!covered_seg[seg_idx]) {
                covered_seg[seg_idx] = true;
                covered_count++;
            }
        }
    }

    int start_sq_idx = sq_index[si][sj];
    if(!selected_sq[start_sq_idx]) {
        S_points.push_back(squares_list[start_sq_idx]);
        selected_sq[start_sq_idx] = true;
    }

    int S_size = S_points.size();
    vector<int> S_node_id(S_size);
    unordered_map<int, int> node_to_S_idx;
    for(int i=0; i<S_size; i++) {
        Point p = S_points[i];
        int idx = sq_index[p.i][p.j];
        S_node_id[i] = idx;
        node_to_S_idx[idx] = i;
    }

    vector<Point> node_to_point(total_squares);
    for(int i=0; i<N; i++)
        for(int j=0; j<N; j++)
            if(road[i][j])
                node_to_point[sq_index[i][j]] = Point(i,j);

    vector<vector<pair<int,int>>> graph(total_squares);
    int dx[4] = {-1,1,0,0};
    int dy[4] = {0,0,-1,1};
    for(int idx=0; idx<total_squares; idx++) {
        Point p = node_to_point[idx];
        for(int d=0; d<4; d++) {
            int ni = p.i + dx[d];
            int nj = p.j + dy[d];
            if(ni>=0 && ni<N && nj>=0 && nj<N && road[ni][nj]) {
                int nidx = sq_index[ni][nj];
                int c = cost[ni][nj];
                graph[idx].push_back({nidx, c});
            }
        }
    }

    vector<vector<long long>> dist_S(S_size, vector<long long>(S_size, 1e18));
    vector<vector<vector<int>>> prev_S(S_size);
    for(int s_idx=0; s_idx<S_size; s_idx++) {
        int source = S_node_id[s_idx];
        vector<long long> dist(total_squares, 1e18);
        vector<int> prev(total_squares, -1);
        dist[source] = 0;
        priority_queue<pair<long long,int>, vector<pair<long long,int>>, greater<pair<long long,int>>> pq;
        pq.push({0, source});
        while(!pq.empty()) {
            auto [d, u] = pq.top(); pq.pop();
            if(d > dist[u]) continue;
            for(auto &edge : graph[u]) {
                int v = edge.first;
                int w = edge.second;
                if(dist[v] > d + w) {
                    dist[v] = d + w;
                    prev[v] = u;
                    pq.push({dist[v], v});
                }
            }
        }
        for(int t_idx=0; t_idx<S_size; t_idx++) {
            int target = S_node_id[t_idx];
            dist_S[s_idx][t_idx] = dist[target];
        }
        prev_S[s_idx] = prev;
    }

    int start_S_idx = node_to_S_idx[start_sq_idx];
    int n = S_size;
    vector<int> order;
    order.push_back(start_S_idx);
    vector<bool> visited_S(n, false);
    visited_S[start_S_idx] = true;
    int current = start_S_idx;
    for(int step=1; step<n; step++) {
        long long best_dist = 1e18;
        int best_next = -1;
        for(int next=0; next<n; next++) {
            if(!visited_S[next] && dist_S[current][next] < best_dist) {
                best_dist = dist_S[current][next];
                best_next = next;
            }
        }
        if(best_next == -1) break;
        order.push_back(best_next);
        visited_S[best_next] = true;
        current = best_next;
    }

    auto compute_cost = [&](vector<int>& ord) -> long long {
        long long total = 0;
        for(int i=0; i<n-1; i++) total += dist_S[ord[i]][ord[i+1]];
        total += dist_S[ord[n-1]][ord[0]];
        return total;
    };
    long long best_cost = compute_cost(order);
    bool improved = true;
    while(improved) {
        improved = false;
        for(int i=1; i<n; i++) {
            for(int j=i+1; j<n; j++) {
                vector<int> new_order = order;
                reverse(new_order.begin()+i, new_order.begin()+j+1);
                long long new_cost = compute_cost(new_order);
                if(new_cost < best_cost) {
                    order = new_order;
                    best_cost = new_cost;
                    improved = true;
                }
            }
        }
    }

    string moves = "";
    auto get_moves = [&](int a_idx, int b_idx) -> string {
        int a_node = S_node_id[a_idx];
        int b_node = S_node_id[b_idx];
        vector<int> path_nodes;
        int cur = b_node;
        while(cur != a_node) {
            path_nodes.push_back(cur);
            cur = prev_S[a_idx][cur];
        }
        path_nodes.push_back(a_node);
        reverse(path_nodes.begin(), path_nodes.end());
        string seg_moves = "";
        for(size_t k=0; k+1<path_nodes.size(); k++) {
            Point p1 = node_to_point[path_nodes[k]];
            Point p2 = node_to_point[path_nodes[k+1]];
            if(p2.i == p1.i-1) seg_moves += "U";
            else if(p2.i == p1.i+1) seg_moves += "D";
            else if(p2.j == p1.j-1) seg_moves += "L";
            else if(p2.j == p1.j+1) seg_moves += "R";
        }
        return seg_moves;
    };

    for(int i=0; i<n; i++) {
        int a = order[i];
        int b = order[(i+1)%n];
        moves += get_moves(a, b);
    }

    cout << moves << endl;

    return 0;
}