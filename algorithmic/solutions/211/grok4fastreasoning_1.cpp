#include <bits/stdc++.h>
using namespace std;

struct Node {
    int id, x, y;
    char type;
};

struct Edge {
    int u, v;
    double cost;
    bool operator<(const Edge& o) const {
        if (cost != o.cost) return cost < o.cost;
        if (u != o.u) return u < o.u;
        return v < o.v;
    }
};

const int MAXM = 3010;
int parent[MAXM];
int rankk[MAXM];
int robots_per[MAXM];

int find(int x) {
    return parent[x] == x ? x : parent[x] = find(parent[x]);
}

void init_uf(int M, const vector<Node>& nodes, int& num_robot_comp) {
    for (int i = 0; i < M; ++i) {
        parent[i] = i;
        rankk[i] = 0;
        robots_per[i] = (nodes[i].type != 'C' ? 1 : 0);
    }
    num_robot_comp = 0;
    for (int i = 0; i < M; ++i) {
        if (nodes[i].type != 'C') ++num_robot_comp;
    }
}

vector<Edge> run_kruskal(const vector<Edge>& all_edges, int M, const vector<Node>& nodes, int& num_robot_comp) {
    init_uf(M, nodes, num_robot_comp);
    vector<Edge> added;
    num_robot_comp = 0; // reset
    init_uf(M, nodes, num_robot_comp); // proper init
    for (const auto& e : all_edges) {
        int pu = find(e.u);
        int pv = find(e.v);
        if (pu == pv) continue;
        int ra = robots_per[pu];
        int rb = robots_per[pv];
        bool merge_robots = (ra > 0 && rb > 0);
        if (merge_robots) --num_robot_comp;
        if (rankk[pu] < rankk[pv]) {
            swap(pu, pv);
        }
        parent[pv] = pu;
        robots_per[pu] += robots_per[pv];
        if (rankk[pu] == rankk[pv]) ++rankk[pu];
        added.push_back(e);
        if (num_robot_comp == 1) break;
    }
    return added;
}

double get_cost(const vector<Edge>& edges) {
    double cost = 0.0;
    for (const auto& e : edges) cost += e.cost;
    return cost;
}

vector<tuple<int, int>> get_link_pairs(const vector<Edge>& final_edges, const vector<Node>& nodes) {
    vector<tuple<int, int>> pairs;
    for (const auto& e : final_edges) {
        int id1 = nodes[e.u].id;
        int id2 = nodes[e.v].id;
        if (id1 > id2) swap(id1, id2);
        pairs.emplace_back(id1, id2);
    }
    sort(pairs.begin(), pairs.end());
    return pairs;
}

set<int> get_used_relays(const vector<Edge>& final_edges, const vector<Node>& nodes) {
    set<int> used;
    for (const auto& e : final_edges) {
        if (nodes[e.u].type == 'C') used.insert(nodes[e.u].id);
        if (nodes[e.v].type == 'C') used.insert(nodes[e.v].id);
    }
    return used;
}

int main() {
    ios::sync_with_stdio(false);
    cin.tie(nullptr);
    int N, K;
    cin >> N >> K;
    int M = N + K;
    vector<Node> nodes(M);
    for (int i = 0; i < M; ++i) {
        cin >> nodes[i].id >> nodes[i].x >> nodes[i].y >> nodes[i].type;
    }
    vector<int> robot_inds;
    for (int i = 0; i < M; ++i) {
        if (nodes[i].type != 'C') robot_inds.push_back(i);
    }
    int num_robots = robot_inds.size();

    // Base MST: only robot-robot edges
    vector<Edge> base_all;
    for (size_t p = 0; p < robot_inds.size(); ++p) {
        for (size_t q = p + 1; q < robot_inds.size(); ++q) {
            int i = robot_inds[p], j = robot_inds[q];
            long long dx = (long long)nodes[i].x - nodes[j].x;
            long long dy = (long long)nodes[i].y - nodes[j].y;
            long long D = dx * dx + dy * dy;
            double cost = (nodes[i].type == 'R' && nodes[j].type == 'R') ? 1.0 * D : 0.8 * D;
            int uu = min(i, j), vv = max(i, j);
            base_all.push_back({uu, vv, cost});
        }
    }
    sort(base_all.begin(), base_all.end());
    int dummy_comp;
    vector<Edge> added_base = run_kruskal(base_all, M, nodes, dummy_comp);

    // Enhanced: all edges
    vector<Edge> all_enh = base_all;
    for (int ri : robot_inds) {
        for (int ci = 0; ci < M; ++ci) {
            if (nodes[ci].type != 'C') continue;
            int i = ri, j = ci;
            long long dx = (long long)nodes[i].x - nodes[j].x;
            long long dy = (long long)nodes[i].y - nodes[j].y;
            long long D = dx * dx + dy * dy;
            double cost = 1.0 * D;
            int uu = min(i, j), vv = max(i, j);
            all_enh.push_back({uu, vv, cost});
        }
    }
    sort(all_enh.begin(), all_enh.end());
    vector<Edge> added_enh = run_kruskal(all_enh, M, nodes, dummy_comp);

    // Prune added_enh
    vector<int> deg(M, 0);
    for (const auto& e : added_enh) {
        ++deg[e.u];
        ++deg[e.v];
    }
    vector<Edge> final_enh;
    for (const auto& e : added_enh) {
        int a = e.u, b = e.v;
        char ta = nodes[a].type, tb = nodes[b].type;
        int relay = -1;
        if (ta == 'C' && tb != 'C') relay = a;
        else if (tb == 'C' && ta != 'C') relay = b;
        bool keep = (relay == -1 || deg[relay] >= 2);
        if (keep) final_enh.push_back(e);
    }

    double base_cost = get_cost(added_base);
    double enh_cost = get_cost(final_enh);

    vector<Edge> chosen_edges;
    set<int> chosen_relay_ids;
    bool use_enh = (enh_cost <= base_cost);
    if (use_enh) {
        chosen_edges = final_enh;
        set<int> used = get_used_relays(final_enh, nodes);
        for (int id : used) chosen_relay_ids.insert(id);
    } else {
        chosen_edges = added_base;
        // no relays
    }

    // Output relays
    vector<int> relay_list(chosen_relay_ids.begin(), chosen_relay_ids.end());
    if (relay_list.empty()) {
        cout << "#" << endl;
    } else {
        string s = to_string(relay_list[0]);
        for (size_t i = 1; i < relay_list.size(); ++i) {
            s += "#" + to_string(relay_list[i]);
        }
        cout << s << endl;
    }

    // Output links
    vector<tuple<int, int>> link_pairs = get_link_pairs(chosen_edges, nodes);
    string ls;
    bool first = true;
    for (const auto& tp : link_pairs) {
        int i1, i2;
        tie(i1, i2) = tp;
        if (!first) ls += "#";
        ls += to_string(i1) + "-" + to_string(i2);
        first = false;
    }
    cout << ls << endl;

    return 0;
}