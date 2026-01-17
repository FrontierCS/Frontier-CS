#include <bits/stdc++.h>
using namespace std;

struct Edge {
    int u, v;
    double cost;
};

int find(vector<int>& par, int i) {
    if (par[i] != i) par[i] = find(par, par[i]);
    return par[i];
}

void unite(vector<int>& par, vector<int>& rankk, int a, int b) {
    a = find(par, a);
    b = find(par, b);
    if (a == b) return;
    if (rankk[a] < rankk[b]) swap(a, b);
    par[b] = a;
    if (rankk[a] == rankk[b]) rankk[a]++;
}

int main() {
    int N, K;
    cin >> N >> K;
    int total = N + K;
    vector<int> idd(total);
    vector<long long> xx(total), yy(total);
    vector<char> typ(total);
    for (int i = 0; i < total; i++) {
        string ts;
        cin >> idd[i] >> xx[i] >> yy[i] >> ts;
        typ[i] = ts[0];
    }

    vector<int> robot_list;
    for (int i = 0; i < total; i++) {
        if (typ[i] != 'C') robot_list.push_back(i);
    }
    int num_robots = robot_list.size();

    // Base MST on robots
    unordered_map<int, int> robot_local;
    for (int loc = 0; loc < num_robots; loc++) {
        robot_local[robot_list[loc]] = loc;
    }
    vector<Edge> edges_base;
    for (int ii = 0; ii < num_robots; ii++) {
        int i = robot_list[ii];
        for (int jj = ii + 1; jj < num_robots; jj++) {
            int j = robot_list[jj];
            long long dx = xx[i] - xx[j];
            long long dy = yy[i] - yy[j];
            long long d = dx * dx + dy * dy;
            double c = (typ[i] == 'R' && typ[j] == 'R') ? 1.0 * d : 0.8 * d;
            edges_base.push_back({i, j, c});
        }
    }
    sort(edges_base.begin(), edges_base.end(), [](const Edge& a, const Edge& b) {
        return a.cost < b.cost;
    });
    vector<int> par_loc(num_robots), rank_loc(num_robots, 0);
    for (int i = 0; i < num_robots; i++) par_loc[i] = i;
    double base_cost = 0.0;
    vector<pair<int, int>> base_links;
    int edges_used = 0;
    for (auto& e : edges_base) {
        int gi = e.u, gj = e.v;
        int li = robot_local[gi], lj = robot_local[gj];
        int pu = find(par_loc, li), pv = find(par_loc, lj);
        if (pu != pv) {
            unite(par_loc, rank_loc, li, lj);
            base_cost += e.cost;
            base_links.push_back({gi, gj});
            edges_used++;
            if (edges_used == num_robots - 1) break;
        }
    }

    // Full MST
    vector<Edge> all_edges = edges_base; // robot-robot
    for (int ri : robot_list) {
        for (int ci = 0; ci < total; ci++) {
            if (typ[ci] == 'C') {
                long long dx = xx[ri] - xx[ci];
                long long dy = yy[ri] - yy[ci];
                long long d = dx * dx + dy * dy;
                double c = 1.0 * d;
                all_edges.push_back({ri, ci, c});
            }
        }
    }
    sort(all_edges.begin(), all_edges.end(), [](const Edge& a, const Edge& b) {
        return a.cost < b.cost;
    });
    vector<int> par(total), rankk(total, 0);
    for (int i = 0; i < total; i++) par[i] = i;
    vector<Edge> mst_edges;
    int comp = total;
    for (auto& e : all_edges) {
        int pu = find(par, e.u), pv = find(par, e.v);
        if (pu != pv) {
            unite(par, rankk, e.u, e.v);
            mst_edges.push_back(e);
            comp--;
            if (comp == 1) break;
        }
    }

    // Build adj for degrees
    vector<vector<int>> adj(total);
    for (auto& e : mst_edges) {
        adj[e.u].push_back(e.v);
        adj[e.v].push_back(e.u);
    }
    vector<int> degree(total, 0);
    for (int i = 0; i < total; i++) {
        degree[i] = adj[i].size();
    }

    // Prune
    double steiner_cost = 0.0;
    vector<Edge> steiner_edges_list;
    for (auto& e : mst_edges) {
        int u = e.u, v = e.v;
        bool remove = false;
        if (typ[u] == 'C' && degree[u] == 1) remove = true;
        if (typ[v] == 'C' && degree[v] == 1) remove = true;
        if (!remove) {
            steiner_edges_list.push_back(e);
            steiner_cost += e.cost;
        }
    }

    // Choose
    bool use_steiner = (steiner_cost < base_cost - 1e-9);
    vector<pair<int, int>> chosen_links;
    set<int> selected_relay_idx;
    if (use_steiner) {
        for (auto& e : steiner_edges_list) {
            chosen_links.push_back({e.u, e.v});
            if (typ[e.u] == 'C') selected_relay_idx.insert(e.u);
            if (typ[e.v] == 'C') selected_relay_idx.insert(e.v);
        }
    } else {
        chosen_links = base_links;
    }

    // Selected relays
    vector<int> sel_ids;
    for (int idx : selected_relay_idx) {
        sel_ids.push_back(idd[idx]);
    }
    sort(sel_ids.begin(), sel_ids.end());
    if (sel_ids.empty()) {
        cout << "#" << endl;
    } else {
        for (size_t j = 0; j < sel_ids.size(); j++) {
            if (j > 0) cout << "#";
            cout << sel_ids[j];
        }
        cout << endl;
    }

    // Links
    vector<pair<int, int>> id_pairs;
    for (auto p : chosen_links) {
        int a = idd[p.first], b = idd[p.second];
        if (a > b) swap(a, b);
        id_pairs.emplace_back(a, b);
    }
    sort(id_pairs.begin(), id_pairs.end());
    if (id_pairs.empty()) {
        cout << "#" << endl;
    } else {
        for (size_t j = 0; j < id_pairs.size(); j++) {
            if (j > 0) cout << "#";
            auto [a, b] = id_pairs[j];
            cout << a << "-" << b;
        }
        cout << endl;
    }

    return 0;
}