#include <bits/stdc++.h>
using namespace std;

struct Edge {
    double cost;
    int u, v, bestk;
    bool operator<(const Edge& other) const {
        return cost < other.cost;
    }
};

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    
    int N, K;
    cin >> N >> K;
    
    vector<int> robot_ids, relay_ids;
    vector<double> robot_x, robot_y;
    vector<char> robot_type;
    vector<double> relay_x, relay_y;
    
    for (int i = 0; i < N + K; ++i) {
        int id;
        double xx, yy;
        string tp;
        cin >> id >> xx >> yy >> tp;
        if (tp == "R" || tp == "S") {
            robot_ids.push_back(id);
            robot_x.push_back(xx);
            robot_y.push_back(yy);
            robot_type.push_back(tp[0]);
        } else {
            relay_ids.push_back(id);
            relay_x.push_back(xx);
            relay_y.push_back(yy);
        }
    }
    
    int NN = robot_ids.size();
    int KK = relay_ids.size();
    
    vector<vector<double>> distR(NN, vector<double>(KK, 0.0));
    for (int i = 0; i < NN; ++i) {
        for (int k = 0; k < KK; ++k) {
            double dx = robot_x[i] - relay_x[k];
            double dy = robot_y[i] - relay_y[k];
            distR[i][k] = dx * dx + dy * dy;
        }
    }
    
    vector<Edge> edges;
    edges.reserve(NN * (NN - 1LL) / 2);
    for (int i = 0; i < NN; ++i) {
        for (int j = i + 1; j < NN; ++j) {
            double dx = robot_x[i] - robot_x[j];
            double dy = robot_y[i] - robot_y[j];
            double d = dx * dx + dy * dy;
            double factor = (robot_type[i] == 'R' && robot_type[j] == 'R') ? 1.0 : 0.8;
            double directc = factor * d;
            
            double minvia = 1e30;
            int bestkk = -1;
            for (int kk = 0; kk < KK; ++kk) {
                double temp = distR[i][kk] + distR[j][kk];
                if (temp < minvia) {
                    minvia = temp;
                    bestkk = kk;
                }
            }
            
            double ec = (minvia < directc - 1e-9) ? minvia : directc; // tolerance for floating point
            int bk = (minvia < directc - 1e-9) ? bestkk : -1;
            
            edges.push_back({ec, i, j, bk});
        }
    }
    
    sort(edges.begin(), edges.end());
    
    vector<int> parent(NN);
    vector<int> rankk(NN, 0);
    for (int i = 0; i < NN; ++i) parent[i] = i;
    
    auto find = [&](auto&& self, int x) -> int {
        if (parent[x] != x) parent[x] = self(self, parent[x]);
        return parent[x];
    };
    
    auto unite = [&](int x, int y) -> bool {
        int px = find(find, x);
        int py = find(find, y);
        if (px == py) return false;
        if (rankk[px] < rankk[py]) swap(px, py);
        parent[py] = px;
        if (rankk[px] == rankk[py]) ++rankk[px];
        return true;
    };
    
    set<pair<int, int>> required_rc; // {robot_idx, relay_idx}
    vector<pair<int, int>> direct_links; // {id1 < id2}
    int num_edges_used = 0;
    
    for (auto& e : edges) {
        int pu = find(find, e.u);
        int pv = find(find, e.v);
        if (pu != pv) {
            if (unite(e.u, e.v)) {
                ++num_edges_used;
                if (e.bestk == -1) {
                    int id1 = robot_ids[e.u];
                    int id2 = robot_ids[e.v];
                    if (id1 > id2) swap(id1, id2);
                    direct_links.emplace_back(id1, id2);
                } else {
                    int r1 = e.u, r2 = e.v, rk = e.bestk;
                    required_rc.emplace(r1, rk);
                    required_rc.emplace(r2, rk);
                }
            }
            if (num_edges_used == NN - 1) break;
        }
    }
    
    set<int> sel_relay_idx;
    for (auto& p : required_rc) {
        sel_relay_idx.insert(p.second);
    }
    
    vector<int> selected;
    for (int idx : sel_relay_idx) {
        selected.push_back(relay_ids[idx]);
    }
    sort(selected.begin(), selected.end());
    
    vector<pair<int, int>> all_links = direct_links;
    for (auto& p : required_rc) {
        int r_idx = p.first;
        int rk_idx = p.second;
        int idr = robot_ids[r_idx];
        int idc = relay_ids[rk_idx];
        int mn = min(idr, idc);
        int mx = max(idr, idc);
        all_links.emplace_back(mn, mx);
    }
    
    sort(all_links.begin(), all_links.end());
    
    // Output selected relays
    if (selected.empty()) {
        cout << "#" << '\n';
    } else {
        for (size_t i = 0; i < selected.size(); ++i) {
            if (i > 0) cout << "#";
            cout << selected[i];
        }
        cout << '\n';
    }
    
    // Output links
    if (all_links.empty()) {
        cout << "#" << '\n';
    } else {
        for (size_t i = 0; i < all_links.size(); ++i) {
            if (i > 0) cout << "#";
            cout << all_links[i].first << "-" << all_links[i].second;
        }
        cout << '\n';
    }
    
    return 0;
}